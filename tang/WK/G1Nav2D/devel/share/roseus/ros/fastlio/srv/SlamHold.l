;; Auto-generated. Do not edit!


(when (boundp 'fastlio::SlamHold)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'SlamHold (find-package "FASTLIO")))
(unless (find-package "FASTLIO::SLAMHOLD")
  (make-package "FASTLIO::SLAMHOLD"))
(unless (find-package "FASTLIO::SLAMHOLDREQUEST")
  (make-package "FASTLIO::SLAMHOLDREQUEST"))
(unless (find-package "FASTLIO::SLAMHOLDRESPONSE")
  (make-package "FASTLIO::SLAMHOLDRESPONSE"))

(in-package "ROS")





(defclass fastlio::SlamHoldRequest
  :super ros::object
  :slots (_code ))

(defmethod fastlio::SlamHoldRequest
  (:init
   (&key
    ((:code __code) 0)
    )
   (send-super :init)
   (setq _code (round __code))
   self)
  (:code
   (&optional __code)
   (if __code (setq _code __code)) _code)
  (:serialization-length
   ()
   (+
    ;; int32 _code
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _code
       (write-long _code s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _code
     (setq _code (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;;
   self)
  )

(defclass fastlio::SlamHoldResponse
  :super ros::object
  :slots (_status _message ))

(defmethod fastlio::SlamHoldResponse
  (:init
   (&key
    ((:status __status) 0)
    ((:message __message) "")
    )
   (send-super :init)
   (setq _status (round __status))
   (setq _message (string __message))
   self)
  (:status
   (&optional __status)
   (if __status (setq _status __status)) _status)
  (:message
   (&optional __message)
   (if __message (setq _message __message)) _message)
  (:serialization-length
   ()
   (+
    ;; int32 _status
    4
    ;; string _message
    4 (length _message)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _status
       (write-long _status s)
     ;; string _message
       (write-long (length _message) s) (princ _message s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _status
     (setq _status (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; string _message
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _message (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;;
   self)
  )

(defclass fastlio::SlamHold
  :super ros::object
  :slots ())

(setf (get fastlio::SlamHold :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamHold :datatype-) "fastlio/SlamHold")
(setf (get fastlio::SlamHold :request) fastlio::SlamHoldRequest)
(setf (get fastlio::SlamHold :response) fastlio::SlamHoldResponse)

(defmethod fastlio::SlamHoldRequest
  (:response () (instance fastlio::SlamHoldResponse :init)))

(setf (get fastlio::SlamHoldRequest :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamHoldRequest :datatype-) "fastlio/SlamHoldRequest")
(setf (get fastlio::SlamHoldRequest :definition-)
      "int32 code
---
int32 status
string message

")

(setf (get fastlio::SlamHoldResponse :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamHoldResponse :datatype-) "fastlio/SlamHoldResponse")
(setf (get fastlio::SlamHoldResponse :definition-)
      "int32 code
---
int32 status
string message

")



(provide :fastlio/SlamHold "70c3acd228da7b83ec6f69864540ea91")


