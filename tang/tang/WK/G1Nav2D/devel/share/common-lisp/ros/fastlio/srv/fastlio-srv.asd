
(cl:in-package :asdf)

(defsystem "fastlio-srv"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "MapConvert" :depends-on ("_package_MapConvert"))
    (:file "_package_MapConvert" :depends-on ("_package"))
    (:file "SaveMap" :depends-on ("_package_SaveMap"))
    (:file "_package_SaveMap" :depends-on ("_package"))
    (:file "SlamHold" :depends-on ("_package_SlamHold"))
    (:file "_package_SlamHold" :depends-on ("_package"))
    (:file "SlamReLoc" :depends-on ("_package_SlamReLoc"))
    (:file "_package_SlamReLoc" :depends-on ("_package"))
    (:file "SlamRelocCheck" :depends-on ("_package_SlamRelocCheck"))
    (:file "_package_SlamRelocCheck" :depends-on ("_package"))
    (:file "SlamStart" :depends-on ("_package_SlamStart"))
    (:file "_package_SlamStart" :depends-on ("_package"))
  ))