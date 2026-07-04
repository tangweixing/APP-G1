;; Auto-generated. Do not edit!


(when (boundp 'fastlio::SlamStart)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'SlamStart (find-package "FASTLIO")))
(unless (find-package "FASTLIO::SLAMSTART")
  (make-package "FASTLIO::SLAMSTART"))
(unless (find-package "FASTLIO::SLAMSTARTREQUEST")
  (make-package "FASTLIO::SLAMSTARTREQUEST"))
(unless (find-package "FASTLIO::SLAMSTARTRESPONSE")
  (make-package "FASTLIO::SLAMSTARTRESPONSE"))

(in-package "ROS")





(defclass fastlio::SlamStartRequest
  :super ros::object
  :slots (_code ))

(defmethod fastlio::SlamStartRequest
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

(defclass fastlio::SlamStartResponse
  :super ros::object
  :slots (_status _message ))

(defmethod fastlio::SlamStartResponse
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

(defclass fastlio::SlamStart
  :super ros::object
  :slots ())

(setf (get fastlio::SlamStart :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamStart :datatype-) "fastlio/SlamStart")
(setf (get fastlio::SlamStart :request) fastlio::SlamStartRequest)
(setf (get fastlio::SlamStart :response) fastlio::SlamStartResponse)

(defmethod fastlio::SlamStartRequest
  (:response () (instance fastlio::SlamStartResponse :init)))

(setf (get fastlio::SlamStartRequest :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamStartRequest :datatype-) "fastlio/SlamStartRequest")
(setf (get fastlio::SlamStartRequest :definition-)
      "int32 code
---
int32 status
string message

")

(setf (get fastlio::SlamStartResponse :md5sum-) "70c3acd228da7b83ec6f69864540ea91")
(setf (get fastlio::SlamStartResponse :datatype-) "fastlio/SlamStartResponse")
(setf (get fastlio::SlamStartResponse :definition-)
      "int32 code
---
int32 status
string message

")



(provide :fastlio/SlamStart "70c3acd228da7b83ec6f69864540ea91")


