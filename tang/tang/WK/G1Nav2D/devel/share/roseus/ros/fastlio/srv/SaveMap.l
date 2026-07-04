;; Auto-generated. Do not edit!


(when (boundp 'fastlio::SaveMap)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'SaveMap (find-package "FASTLIO")))
(unless (find-package "FASTLIO::SAVEMAP")
  (make-package "FASTLIO::SAVEMAP"))
(unless (find-package "FASTLIO::SAVEMAPREQUEST")
  (make-package "FASTLIO::SAVEMAPREQUEST"))
(unless (find-package "FASTLIO::SAVEMAPRESPONSE")
  (make-package "FASTLIO::SAVEMAPRESPONSE"))

(in-package "ROS")





(defclass fastlio::SaveMapRequest
  :super ros::object
  :slots (_save_path _resolution ))

(defmethod fastlio::SaveMapRequest
  (:init
   (&key
    ((:save_path __save_path) "")
    ((:resolution __resolution) 0.0)
    )
   (send-super :init)
   (setq _save_path (string __save_path))
   (setq _resolution (float __resolution))
   self)
  (:save_path
   (&optional __save_path)
   (if __save_path (setq _save_path __save_path)) _save_path)
  (:resolution
   (&optional __resolution)
   (if __resolution (setq _resolution __resolution)) _resolution)
  (:serialization-length
   ()
   (+
    ;; string _save_path
    4 (length _save_path)
    ;; float32 _resolution
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; string _save_path
       (write-long (length _save_path) s) (princ _save_path s)
     ;; float32 _resolution
       (sys::poke _resolution (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; string _save_path
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _save_path (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; float32 _resolution
     (setq _resolution (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;;
   self)
  )

(defclass fastlio::SaveMapResponse
  :super ros::object
  :slots (_status _message ))

(defmethod fastlio::SaveMapResponse
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

(defclass fastlio::SaveMap
  :super ros::object
  :slots ())

(setf (get fastlio::SaveMap :md5sum-) "2ecd66ba01bbd96308e3355e33bda01e")
(setf (get fastlio::SaveMap :datatype-) "fastlio/SaveMap")
(setf (get fastlio::SaveMap :request) fastlio::SaveMapRequest)
(setf (get fastlio::SaveMap :response) fastlio::SaveMapResponse)

(defmethod fastlio::SaveMapRequest
  (:response () (instance fastlio::SaveMapResponse :init)))

(setf (get fastlio::SaveMapRequest :md5sum-) "2ecd66ba01bbd96308e3355e33bda01e")
(setf (get fastlio::SaveMapRequest :datatype-) "fastlio/SaveMapRequest")
(setf (get fastlio::SaveMapRequest :definition-)
      "string save_path
float32 resolution
---
int32 status
string message
")

(setf (get fastlio::SaveMapResponse :md5sum-) "2ecd66ba01bbd96308e3355e33bda01e")
(setf (get fastlio::SaveMapResponse :datatype-) "fastlio/SaveMapResponse")
(setf (get fastlio::SaveMapResponse :definition-)
      "string save_path
float32 resolution
---
int32 status
string message
")



(provide :fastlio/SaveMap "2ecd66ba01bbd96308e3355e33bda01e")


