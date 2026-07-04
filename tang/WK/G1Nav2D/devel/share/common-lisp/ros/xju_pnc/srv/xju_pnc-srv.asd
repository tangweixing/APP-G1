
(cl:in-package :asdf)

(defsystem "xju_pnc-srv"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "xju_task" :depends-on ("_package_xju_task"))
    (:file "_package_xju_task" :depends-on ("_package"))
  ))