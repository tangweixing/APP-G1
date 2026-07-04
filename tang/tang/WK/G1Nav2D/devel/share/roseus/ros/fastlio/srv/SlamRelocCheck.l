;; Auto-generated. Do not edit!


(when (boundp 'fastlio::SlamRelocCheck)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'SlamRelocCheck (find-package "FASTLIO")))
(unless (find-package "FASTLIO::SLAMRELOCCHECK")
  (make-package "FASTLIO::SLAMRELOCCHECK"))
(unless (find-package "FASTLIO::SLAMRELOCCHECKREQUEST")
  (make-package "FASTLIO::SLAMRELOCCHECKREQUEST"))
(unless (find-package "FASTLIO::SLAMRELOCCHECKRESPONSE")
  (make-package "FASTLIO::SLAMRELOCCHECKRESPONSE"))

(in-package "ROS")





(defclass fastlio::SlamRelocCheckRequest
  :super ros::object
  :slots (_code ))

(defmethod fastlio::SlamRelocCheckRequest
  (:init
   (&key
    ((:code __code) nil)
    )
   (send-super :init)
   (setq _code __code)
   self)
  (:code
   (&optional (__code :null))
   (if (not (eq __code :null)) (setq _code __code)) _code)
  (:serialization-length
   ()
   (+
    ;; bool _code
    1
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; bool _code
       (if _code (write-byte -1 s) (write-byte 0 s))
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; bool _code
     (setq _code (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;;
   self)
  )

(defclass fastlio::SlamRelocCheckResponse
  :super ros::object
  :slots (_status ))

(defmethod fastlio::SlamRelocCheckResponse
  (:init
   (&key
    ((:status __status) nil)
    )
   (send-super :init)
   (setq _status __status)
   self)
  (:status
   (&optional (__status :null))
   (if (not (eq __status :null)) (setq _status __status)) _status)
  (:serialization-length
   ()
   (+
    ;; bool _status
    1
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; bool _status
       (if _status (write-byte -1 s) (write-byte 0 s))
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; bool _status
     (setq _status (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;;
   self)
  )

(defclass fastlio::SlamRelocCheck
  :super ros::object
  :slots ())

(setf (get fastlio::SlamRelocCheck :md5sum-) "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(setf (get fastlio::SlamRelocCheck :datatype-) "fastlio/SlamRelocCheck")
(setf (get fastlio::SlamRelocCheck :request) fastlio::SlamRelocCheckRequest)
(setf (get fastlio::SlamRelocCheck :response) fastlio::SlamRelocCheckResponse)

(defmethod fastlio::SlamRelocCheckRequest
  (:response () (instance fastlio::SlamRelocCheckResponse :init)))

(setf (get fastlio::SlamRelocCheckRequest :md5sum-) "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(setf (get fastlio::SlamRelocCheckRequest :datatype-) "fastlio/SlamRelocCheckRequest")
(setf (get fastlio::SlamRelocCheckRequest :definition-)
      "bool code
---
bool status
")

(setf (get fastlio::SlamRelocCheckResponse :md5sum-) "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(setf (get fastlio::SlamRelocCheckResponse :datatype-) "fastlio/SlamRelocCheckResponse")
(setf (get fastlio::SlamRelocCheckResponse :definition-)
      "bool code
---
bool status
")



(provide :fastlio/SlamRelocCheck "6fa8ef0c716a8f69e2ee4f999bd02a6e")


