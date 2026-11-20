# kotlinx.serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class org.openpm.**$$serializer { *; }
-keepclassmembers class org.openpm.** { *** Companion; }
-keepclasseswithmembers class org.openpm.** { kotlinx.serialization.KSerializer serializer(...); }
