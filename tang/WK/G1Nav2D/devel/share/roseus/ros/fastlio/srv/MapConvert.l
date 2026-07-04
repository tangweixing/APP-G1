;; Auto-generated. Do not edit!


(when (boundp 'fastlio::MapConvert)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'MapConvert (find-package "FASTLIO")))
(unless (find-package "FASTLIO::MAPCONVERT")
  (make-package "FASTLIO::MAPCONVERT"))
(unless (find-package "FASTLIO::MAPCONVERTREQUEST")
  (make-package "FASTLIO::MAPCONVERTREQUEST"))
(unless (find-package "FASTLIO::MAPCONVERTRESPONSE")
  (make-package "FASTLIO::MAPCONVERTRESPONSE"))

(in-package "ROS")





(defclass fastlio::MapConvertRequest
  :super ros::object
  :slots (_map_path _save_path _resolution ))

(defmethod fastlio::MapConvertRequest
  (:init
   (&key
    ((:map_path __map_path) "")
    ((:save_path __save_path) "")
    ((:resolution __resolution) 0.0)
    )
   (send-super :init)
   (setq _map_path (string __map_path))
   (setq _save_path (string __save_path))
   (setq _resolution (float __resolution))
   self)
  (:map_path
   (&optional __map_path)
   (if __map_path (setq _map_path __map_path)) _map_path)
  (:save_path
   (&optional __save_path)
   (if __save_path (setq _save_path __save_path)) _save_path)
  (:resolution
   (&optional __resolution)
   (if __resolution (setq _resolution __resolution)) _resolution)
  (:serialization-length
   ()
   (+
    ;; string _map_path
    4 (length _map_path)
    ;; string _save_path
    4 (length _save_path)
    ;; float32 _resolution
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; string _map_path
       (write-long (length _map_path) s) (princ _map_path s)
     ;; string _save_path
       (write-long (length _save_path) s) (princ _save_path s)
     ;; float32 _resolution
       (sys::poke _resolution (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; string _map_path
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _map_path (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; string _save_path
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _save_path (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; float32 _resolution
     (setq _resolution (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;;
   self)
  )

(defclass fastlio::MapConvertResponse
  :super ros::object
  :slots (_status _message ))

(defmethod fastlio::MapConvertResponse
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

(defclass fastlio::MapConvert
  :super ros::object
  :slots ())

(setf (get fastlio::MapConvert :md5sum-) "27938b198ec2a6b94cdc450d4db81e6d")
(setf (get fastlio::MapConvert :datatype-) "fastlio/MapConvert")
(setf (get fastlio::MapConvert :request) fastlio::MapConvertRequest)
(setf (get fastlio::MapConvert :response) fastlio::MapConvertResponse)

(defmethod fastlio::MapConvertRequest
  (:response () (instance fastlio::MapConvertResponse :init)))

(setf (get fastlio::MapConvertRequest :md5sum-) "27938b198ec2a6b94cdc450d4db81e6d")
(setf (get fastlio::MapConvertRequest :datatype-) "fastlio/MapConvertRequest")
(setf (get fastlio::MapConvertRequest :definition-)
      "string map_path
string save_path
float32 resolution
---
int32 status
string message
")

(setf (get fastlio::MapConvertResponse :md5sum-) "27938b198ec2a6b94cdc450d4db81e6d")
(setf (get fastlio::MapConvertResponse :datatype-) "fastlio/MapConvertResponse")
(setf (get fastlio::MapConvertResponse :definition-)
      "string map_path
string save_path
float32 resolution
---
int32 status
string message
")



(provide :fastlio/MapConvert "27938b198ec2a6b94cdc450d4db81e6d")


