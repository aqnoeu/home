package com.aqnoeu.home

import android.app.Activity
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsKokoroModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.atomic.AtomicBoolean
import java.util.zip.ZipInputStream

/** Kokoro v1.0 pt-BR, voice id 43 pm_alex — synthesis on the Android device, without server. */
object AlexOffline {
    private const val MODEL_URL =
        "https://huggingface.co/cristianoaredes/kokoro-pt-br/resolve/main/letrinhas-kokoro-pt.zip?download=true"
    private const val ALEX_SID = 43
    private const val MAX_ARCHIVE = 430L * 1024 * 1024
    private const val MAX_UNPACKED = 680L * 1024 * 1024
    private val installing = AtomicBoolean(false)
    private val talking = AtomicBoolean(false)

    fun interface Status {
        fun onStatus(message: String)
    }

    @JvmStatic
    fun isInstalled(context: Context): Boolean = complete(modelDir(context))

    @JvmStatic
    fun isBusy(): Boolean = installing.get()

    private fun modelDir(context: Context) = File(context.filesDir, "kokoro-alex-pt-v1")

    private fun complete(folder: File): Boolean =
        File(folder, "model.onnx").let { it.isFile && it.length() > 220_000_000 } &&
        File(folder, "voices.bin").let { it.isFile && it.length() > 5_000_000 } &&
        File(folder, "tokens.txt").let { it.isFile && it.length() > 100 } &&
        File(folder, "espeak-ng-data").isDirectory

    private fun notice(activity: Activity, callback: Status, text: String) {
        activity.runOnUiThread { if (!activity.isFinishing) callback.onStatus(text) }
    }

    /**
     * One-time opt-in model download (~329 MB). Never silently downloads a model.
     * The archive is untrusted: bounded sizes, controlled extraction paths and structural checks.
     */
    @JvmStatic
    fun installAsync(activity: Activity, callback: Status) {
        if (isInstalled(activity)) {
            callback.onStatus("✓ Alex já instalada. A voz funciona offline.")
            return
        }
        if (!installing.compareAndSet(false, true)) {
            callback.onStatus("A instalação de Alex já está em andamento.")
            return
        }
        val app = activity.applicationContext
        Thread {
            val archive = File(app.cacheDir, "alex-model-download.zip")
            val staged = File(app.filesDir, "kokoro-alex-staging")
            try {
                if (app.filesDir.usableSpace < 850L * 1024 * 1024)
                    error("Libere aproximadamente 850 MB para baixar e instalar a voz Alex.")
                notice(activity, callback, "Baixando Alex (~329 MB). Faça isso no Wi-Fi.")
                val connection = URL(MODEL_URL).openConnection() as HttpURLConnection
                connection.connectTimeout = 20000
                connection.readTimeout = 60000
                connection.instanceFollowRedirects = true
                try {
                    if (connection.responseCode != 200) error("Download indisponível (HTTP ${connection.responseCode}).")
                    if (connection.contentLengthLong > MAX_ARCHIVE)
                        error("Arquivo maior do que o tamanho permitido.")
                    connection.inputStream.use { input ->
                        FileOutputStream(archive).use { output ->
                            val buffer = ByteArray(128 * 1024)
                            var total = 0L
                            var lastNotice = 0L
                            while (true) {
                                val count = input.read(buffer)
                                if (count < 0) break
                                total += count
                                if (total > MAX_ARCHIVE) error("O download excedeu o limite.")
                                output.write(buffer, 0, count)
                                if (total - lastNotice >= 20L * 1024 * 1024) {
                                    lastNotice = total
                                    notice(activity, callback, "Alex: ${total / 1048576} MB baixados…")
                                }
                            }
                            if (total < 100L * 1024 * 1024)
                                error("Download incompleto. Tente novamente pelo Wi-Fi.")
                        }
                    }
                } finally {
                    connection.disconnect()
                }
                if (staged.exists()) staged.deleteRecursively()
                if (!staged.mkdirs()) error("Não foi possível criar a pasta do modelo.")
                notice(activity, callback, "Extraindo o modelo de voz…")
                var unpacked = 0L
                ZipInputStream(archive.inputStream().buffered()).use { zip ->
                    while (true) {
                        val entry = zip.nextEntry ?: break
                        val name = entry.name.replace('\\', '/')
                        // Keep only the exact model resources; ignore all metadata and other files.
                        val espeakPos = name.indexOf("espeak-ng-data/")
                        val relative = if (espeakPos >= 0) {
                            name.substring(espeakPos)
                        } else {
                            val basename = name.substringAfterLast('/')
                            if (basename in setOf("model.onnx", "voices.bin", "tokens.txt")) basename else ""
                        }
                        if (relative.isNotEmpty() && !relative.split('/').contains("..")) {
                            val dest = File(staged, relative).canonicalFile
                            if (!dest.path.startsWith(staged.canonicalPath + File.separator))
                                error("Caminho inválido no modelo.")
                            if (entry.isDirectory) {
                                dest.mkdirs()
                            } else {
                                dest.parentFile?.mkdirs()
                                FileOutputStream(dest).use { out ->
                                    val buffer = ByteArray(128 * 1024)
                                    while (true) {
                                        val count = zip.read(buffer)
                                        if (count < 0) break
                                        unpacked += count
                                        if (unpacked > MAX_UNPACKED)
                                            error("Pacote extraído excedeu o limite.")
                                        out.write(buffer, 0, count)
                                    }
                                }
                            }
                        }
                        zip.closeEntry()
                    }
                }
                if (!complete(staged)) error("O pacote baixado não contém os arquivos Kokoro esperados.")
                val target = modelDir(app)
                if (target.exists() && !target.deleteRecursively())
                    error("Não foi possível substituir o modelo incompleto.")
                if (!staged.renameTo(target))
                    error("Não foi possível concluir a instalação.")
                notice(activity, callback, "✓ Alex instalada! Agora a voz é gerada no próprio celular, offline.")
            } catch (e: Exception) {
                Log.e("HomeAlex", "Falha na instalação local", e)
                notice(activity, callback, "Alex não instalada: ${e.message ?: "erro desconhecido"}")
            } finally {
                archive.delete()
                if (staged.exists()) staged.deleteRecursively()
                installing.set(false)
            }
        }.start()
    }

    @JvmStatic
    fun speak(activity: Activity, text: String, callback: Status) {
        if (!isInstalled(activity)) {
            callback.onStatus("Alex ainda não instalada. Abra Voz e toque em Instalar Alex.")
            return
        }
        if (!talking.compareAndSet(false, true)) {
            callback.onStatus("Alex está falando. Aguarde o fim da frase.")
            return
        }
        val app = activity.applicationContext
        Thread {
            var engine: OfflineTts? = null
            try {
                notice(activity, callback, "Alex está preparando a fala offline…")
                val folder = modelDir(app)
                val kokoro = OfflineTtsKokoroModelConfig(
                    model = File(folder, "model.onnx").absolutePath,
                    voices = File(folder, "voices.bin").absolutePath,
                    tokens = File(folder, "tokens.txt").absolutePath,
                    dataDir = File(folder, "espeak-ng-data").absolutePath,
                    lang = "pt"
                )
                engine = OfflineTts(
                    config = OfflineTtsConfig(
                        model = OfflineTtsModelConfig(kokoro = kokoro, numThreads = 4)
                    )
                )
                if (engine.numSpeakers() <= ALEX_SID)
                    error("O modelo não contém a voz pm_alex (43).")
                val generated = engine.generate(text.take(500), sid = ALEX_SID, speed = 1.0f)
                val samples = generated.samples
                if (samples.isEmpty()) error("O modelo não produziu áudio.")
                val sampleRate = generated.sampleRate
                val minBuffer = AudioTrack.getMinBufferSize(
                    sampleRate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT
                )
                if (minBuffer <= 0) error("Formato de áudio não suportado.")
                val player = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder().setSampleRate(sampleRate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build()
                    )
                    .setBufferSizeInBytes(maxOf(minBuffer, 32768))
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()
                try {
                    notice(activity, callback, "▶ Tocando Alex (Kokoro local)")
                    player.play()
                    val chunk = ShortArray(8192)
                    var offset = 0
                    while (offset < samples.size) {
                        val n = minOf(chunk.size, samples.size - offset)
                        for (i in 0 until n) {
                            chunk[i] = (samples[offset + i].coerceIn(-1f, 1f) * 32767).toInt().toShort()
                        }
                        var written = 0
                        while (written < n) {
                            val count = player.write(chunk, written, n - written, AudioTrack.WRITE_BLOCKING)
                            if (count <= 0) error("Falha na saída de áudio.")
                            written += count
                        }
                        offset += n
                    }
                    // AudioTrack.write queues samples. Wait for the entire phrase rather than
                    // stopping playback immediately (the initial implementation cut speech).
                    val deadline = System.currentTimeMillis() +
                        (samples.size * 1000L / sampleRate).coerceAtMost(90000L) + 3000L
                    while (player.playbackHeadPosition.toLong() < samples.size.toLong() &&
                           System.currentTimeMillis() < deadline) {
                        Thread.sleep(75)
                    }
                } finally {
                    try { player.stop() } catch (_: Exception) {}
                    player.release()
                }
                notice(activity, callback, "✓ Alex reproduzida offline.")
            } catch (e: Throwable) {
                Log.e("HomeAlex", "Erro na síntese Kokoro local", e)
                notice(activity, callback, "Falha na voz Alex local: ${e.message ?: "motor indisponível"}")
            } finally {
                try { engine?.release() } catch (_: Throwable) {}
                talking.set(false)
            }
        }.start()
    }
}
