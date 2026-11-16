plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android {
    namespace = "com.aqnoeu.home"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.aqnoeu.home"
        minSdk = 26
        targetSdk = 35
        versionCode = 115
        versionName = "0.1.15"
        // Optional owner-provided credential injected by a private GitHub Actions Secret.
        // WARNING: an embedded client key can be extracted from a public APK.
        val groqKey = providers.environmentVariable("HOME_GROQ_API_KEY").orNull ?: ""
        require(groqKey.isEmpty() || groqKey.matches(Regex("gsk_[A-Za-z0-9_-]{20,200}"))) {
            "HOME_GROQ_API_KEY must be a valid Groq API key without whitespace"
        }
        buildConfigField("String", "HOME_GROQ_API_KEY", "\"${groqKey}\"")
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
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("org.apache.commons:commons-compress:1.27.1")
    implementation("com.google.zxing:core:3.5.3")
    implementation("androidx.core:core:1.15.0")
}
