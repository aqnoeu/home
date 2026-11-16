plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android {
    namespace = "com.aqnoeu.home"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.aqnoeu.home"
        minSdk = 26
        targetSdk = 35
        // Both desktop and Android receive the same version from one release pipeline.
        val homeVersion = providers.environmentVariable("HOME_RELEASE_VERSION").orNull ?: "2.0.0"
        val parts = homeVersion.split(".").map { it.toInt() }
        require(parts.size == 3 && parts.all { it >= 0 } && parts[1] < 100 && parts[2] < 10000)
        versionCode = parts[0] * 1000000 + parts[1] * 10000 + parts[2]
        versionName = homeVersion

    }
    signingConfigs {
        create("releaseKey") {
            val store = providers.environmentVariable("HOME_KEYSTORE_PATH").orNull
            if (!store.isNullOrBlank()) storeFile = file(store)
            storePassword = providers.environmentVariable("HOME_KEYSTORE_PASSWORD").orNull
            keyAlias = providers.environmentVariable("HOME_KEY_ALIAS").orNull
            keyPassword = providers.environmentVariable("HOME_KEY_PASSWORD").orNull
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            if (!providers.environmentVariable("HOME_KEYSTORE_PATH").orNull.isNullOrBlank()) {
                signingConfig = signingConfigs.getByName("releaseKey")
            }
        }
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation(files("libs/sherpa-onnx.aar"))
    implementation("com.alphacephei:vosk-android:0.3.75")
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("org.apache.commons:commons-compress:1.27.1")
    implementation("com.google.zxing:core:3.5.3")
    implementation("androidx.core:core:1.15.0")
}
