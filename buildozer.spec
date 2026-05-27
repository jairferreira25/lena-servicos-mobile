[app]
title = Lena Servicos
package.name = lenaservicos
package.domain = org.lena
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf
version = 1.0.0
requirements = python3,kivy,kivymd==1.1.1,fpdf2,plyer,pyperclip,Pillow,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools = 33.0.2
android.gradle_dependencies = androidx.core:core:1.9.0
android.enable_androidx = True
android.copy_libs = 1
android.archs = armeabi-v7a, arm64-v8a
android.add_src = .

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1

[deploy]
android.adb_timeout = 60
