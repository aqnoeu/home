package com.aqnoeu.home

import android.app.Activity
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Build
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream

/** Piper Faber pt-BR through sherpa-onnx, same model archive as Home Windows. */
object FaberOffline {
    private const val MODEL_NAME = "vits-piper-pt_BR-faber-medium"
    private const val MODEL_URL =
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/" +
        "vits-piper-pt_BR-faber-medium.tar.bz2"
    private const val EXPECTED_SHA256 = "7add3f923ad6bc25ca8a192805fd1a64d1b3893e4611c4a9719545a825039a83"
    private const val MAX_ARCHIVE = 90L * 1024L * 1024L
    private const val MAX_EXTRACT = 130L * 1024L * 1024L
    private val installing = AtomicBoolean(false)
    private val talking = AtomicBoolean(false)
    @Volatile private var lastProblem = ""
    @Volatile private var stage = "Aguardando teste"

    fun interface Status { fun onStatus(message: String) }

    private fun folder(context: Context) = File(context.filesDir, "piper-faber-pt-br-v1")
    private fun complete(root: File) =
        File(root,"pt_BR-faber-medium.onnx").let { it.isFile && it.length() > 40_000_000 } &&
        File(root,"tokens.txt").let { it.isFile && it.length() > 100 } &&
        File(root,"espeak-ng-data").isDirectory

    @JvmStatic fun isInstalled(context: Context) = complete(folder(context))

    private fun report(activity: Activity, callback: Status, message: String) {
        stage = message
        activity.runOnUiThread { if (!activity.isFinishing) callback.onStatus(message) }
    }

    @JvmStatic fun diagnostic(context: Context): String {
        val root = folder(context)
        val files = listOf("pt_BR-faber-medium.onnx", "tokens.txt", "espeak-ng-data")
        return "Home Faber — diagnóstico\n" +
            "Instalada: " + isInstalled(context) + "\n" +
            "Etapa: " + stage + "\n" +
            "Falha: " + (lastProblem.ifBlank { "nenhuma nesta sessão" }) + "\n" +
            "Arquitetura: " + Build.SUPPORTED_ABIS.joinToString() + "\n" +
            files.joinToString("\n") { name ->
                val f = File(root,name)
                name + ": " + when {
                    f.isDirectory -> "pasta presente"
                    f.isFile -> f.length().toString() + " bytes"
                    else -> "ausente"
                }
            }
    }

    @JvmStatic fun installAsync(activity: Activity, callback: Status) {
        if(isInstalled(activity)) { callback.onStatus("✓ Faber já instalada."); return }
        if(!installing.compareAndSet(false,true)) {
            callback.onStatus("Faber já está sendo instalada.");return
        }
        lastProblem = ""
        val context = activity.applicationContext
        Thread {
            val archive = File(context.cacheDir, "faber-model.tar.bz2")
            val staged = File(context.filesDir, "faber-staging")
            try {
                if(context.filesDir.usableSpace < 250L*1024*1024)
                    error("Libere pelo menos 250 MB temporários para instalar Faber.")
                report(activity,callback,"Baixando Faber (~67 MB)…")
                val connection = URL(MODEL_URL).openConnection() as HttpURLConnection
                connection.connectTimeout = 20000
                connection.readTimeout = 60000
                connection.instanceFollowRedirects = true
                val md = MessageDigest.getInstance("SHA-256")
                try {
                    if(connection.responseCode != 200)
                        error("Download HTTP " + connection.responseCode)
                    var total = 0L
                    connection.inputStream.use { input ->
                        FileOutputStream(archive).use { output ->
                            val buffer = ByteArray(128*1024)
                            while(true) {
                                val n=input.read(buffer)
                                if(n<0) break
                                if(n==0) continue
                                total += n
                                if(total>MAX_ARCHIVE)error("Arquivo maior que o permitido.")
                                md.update(buffer,0,n)
                                output.write(buffer,0,n)
                                if(total % (8L*1024*1024) < n)
                                    report(activity,callback,"Faber: " + total/1048576 + " MB baixados")
                            }
                        }
                    }
                    if(total<40_000_000)error("Arquivo incompleto.")
                }finally {connection.disconnect()}
                val digest=md.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
                if(digest != EXPECTED_SHA256)
                    error("Modelo não passou na verificação de integridade.")
                report(activity,callback,"Extraindo Faber…")
                if(staged.exists())staged.deleteRecursively()
                if(!staged.mkdirs())error("Não foi possível preparar armazenamento.")
                var uncompressed=0L
                TarArchiveInputStream(
                    BZip2CompressorInputStream(archive.inputStream().buffered(),true)
                ).use { tar ->
                    while(true) {
                        val member=tar.nextEntry ?: break
                        if(!member.isFile || member.isSymbolicLink || member.isLink)continue
                        val name=member.name.replace('\\','/')
                        val prefix = "$MODEL_NAME/"
                        if(!name.startsWith(prefix))continue
                        val relative=name.substring(prefix.length)
                        if(relative.split('/').contains(".."))continue
                        if(relative!="pt_BR-faber-medium.onnx" &&
                           relative!="tokens.txt" &&
                           !relative.startsWith("espeak-ng-data/"))continue
                        val output=File(staged,relative).canonicalFile
                        if(!output.path.startsWith(staged.canonicalPath + File.separator))
                            error("Caminho do modelo inválido.")
                        output.parentFile?.mkdirs()
                        FileOutputStream(output).use { out ->
                            var remaining=member.size
                            val buffer=ByteArray(128*1024)
                            while(remaining>0) {
                                val n=tar.read(buffer,0,minOf(remaining,buffer.size.toLong()).toInt())
                                if(n<=0)error("Pacote Faber incompleto.")
                                uncompressed+=n
                                if(uncompressed>MAX_EXTRACT)error("Pacote excedeu o limite.")
                                out.write(buffer,0,n)
                                remaining-=n
                            }
                        }
                    }
                }
                if(!complete(staged))
                    error("O pacote não contém o modelo Faber esperado.")
                val target=folder(context)
                if(target.exists() && !target.deleteRecursively())
                    error("Não foi possível remover o modelo incompleto.")
                if(!staged.renameTo(target))error("Não foi possível salvar a voz Faber.")
                report(activity,callback,"✓ Faber instalada. Agora funciona offline.")
            } catch(e: Throwable) {
                Log.e("HomeFaber","Instalação falhou",e)
                lastProblem = ("Instalação: " + e.javaClass.simpleName + " " + (e.message?:"")).take(300)
                report(activity,callback,"Falha na instalação da Faber. Veja Diagnóstico.")
            } finally {
                archive.delete()
                if(staged.exists())staged.deleteRecursively()
                installing.set(false)
            }
        }.start()
    }

    @JvmStatic fun speak(activity: Activity, text: String, callback: Status) {
        if(!isInstalled(activity)) {
            callback.onStatus("Instale Faber antes de testar.");return
        }
        if(!talking.compareAndSet(false,true)){
            callback.onStatus("O Home já está falando.");return
        }
        lastProblem=""
        val context=activity.applicationContext
        Thread {
            var tts: OfflineTts? = null
            try {
                report(activity,callback,"Carregando Faber no dispositivo…")
                val root=folder(context)
                val vits=OfflineTtsVitsModelConfig(
                    model=File(root,"pt_BR-faber-medium.onnx").absolutePath,
                    tokens=File(root,"tokens.txt").absolutePath,
                    dataDir=File(root,"espeak-ng-data").absolutePath
                )
                tts=OfflineTts(
                    config=OfflineTtsConfig(
                        model=OfflineTtsModelConfig(vits=vits,numThreads=2)
                    )
                )
                report(activity,callback,"Sintetizando a fala com Faber…")
                val generated=tts.generate(text.take(500),sid=0,speed=1.0f)
                val samples=generated.samples
                val sampleRate=generated.sampleRate
                if(samples.isEmpty() || sampleRate<=0)
                    error("A síntese não produziu áudio.")
                val minBuffer=AudioTrack.getMinBufferSize(
                    sampleRate,AudioFormat.CHANNEL_OUT_MONO,AudioFormat.ENCODING_PCM_16BIT)
                if(minBuffer<=0)error("A saída de áudio não é compatível.")
                val player=AudioTrack.Builder()
                    .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
                    .setAudioFormat(AudioFormat.Builder().setSampleRate(sampleRate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                    .setBufferSizeInBytes(maxOf(minBuffer,32768))
                    .setTransferMode(AudioTrack.MODE_STREAM).build()
                try {
                    report(activity,callback,"▶ Reproduzindo Faber")
                    player.play()
                    val chunk=ShortArray(8192)
                    var offset=0
                    while(offset<samples.size){
                        val count=minOf(chunk.size,samples.size-offset)
                        for(i in 0 until count)
                            chunk[i]=(samples[offset+i].coerceIn(-1f,1f)*32767).toInt().toShort()
                        var written=0
                        while(written<count){
                            val n=player.write(chunk,written,count-written,AudioTrack.WRITE_BLOCKING)
                            if(n<=0)error("Falha na saída de som.")
                            written+=n
                        }
                        offset+=count
                    }
                    val deadline=System.currentTimeMillis()+
                        (samples.size*1000L/sampleRate).coerceAtMost(90000L)+3000L
                    while(player.playbackHeadPosition.toLong()<samples.size.toLong() &&
                          System.currentTimeMillis()<deadline)Thread.sleep(50)
                }finally {
                    try{player.stop()}catch(_:Exception){}
                    player.release()
                }
                report(activity,callback,"✓ Faber reproduzida offline.")
            } catch(e: Throwable) {
                Log.e("HomeFaber","Síntese falhou",e)
                lastProblem = (stage+": "+e.javaClass.simpleName+" "+(e.message?:"")).take(300)
                report(activity,callback,"Falha ao reproduzir Faber. Veja Diagnóstico.")
            }finally{
                try{tts?.release()}catch(_:Throwable){}
                talking.set(false)
            }
        }.start()
    }
}
