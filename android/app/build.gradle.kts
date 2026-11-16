plugins { id("com.android.application") }

android {
    namespace = "com.aqnoeu.home"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.aqnoeu.home"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
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
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation("com.google.zxing:core:3.5.3")
}
