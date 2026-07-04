// Auto-generated. Do not edit!

// (in-package fastlio.srv)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------


//-----------------------------------------------------------

class MapConvertRequest {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.map_path = null;
      this.save_path = null;
      this.resolution = null;
    }
    else {
      if (initObj.hasOwnProperty('map_path')) {
        this.map_path = initObj.map_path
      }
      else {
        this.map_path = '';
      }
      if (initObj.hasOwnProperty('save_path')) {
        this.save_path = initObj.save_path
      }
      else {
        this.save_path = '';
      }
      if (initObj.hasOwnProperty('resolution')) {
        this.resolution = initObj.resolution
      }
      else {
        this.resolution = 0.0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type MapConvertRequest
    // Serialize message field [map_path]
    bufferOffset = _serializer.string(obj.map_path, buffer, bufferOffset);
    // Serialize message field [save_path]
    bufferOffset = _serializer.string(obj.save_path, buffer, bufferOffset);
    // Serialize message field [resolution]
    bufferOffset = _serializer.float32(obj.resolution, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type MapConvertRequest
    let len;
    let data = new MapConvertRequest(null);
    // Deserialize message field [map_path]
    data.map_path = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [save_path]
    data.save_path = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [resolution]
    data.resolution = _deserializer.float32(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.map_path);
    length += _getByteLength(object.save_path);
    return length + 12;
  }

  static datatype() {
    // Returns string type for a service object
    return 'fastlio/MapConvertRequest';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return 'a3107f9e4cf7e95be092905d828311cf';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    string map_path
    string save_path
    float32 resolution
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new MapConvertRequest(null);
    if (msg.map_path !== undefined) {
      resolved.map_path = msg.map_path;
    }
    else {
      resolved.map_path = ''
    }

    if (msg.save_path !== undefined) {
      resolved.save_path = msg.save_path;
    }
    else {
      resolved.save_path = ''
    }

    if (msg.resolution !== undefined) {
      resolved.resolution = msg.resolution;
    }
    else {
      resolved.resolution = 0.0
    }

    return resolved;
    }
};

class MapConvertResponse {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.status = null;
      this.message = null;
    }
    else {
      if (initObj.hasOwnProperty('status')) {
        this.status = initObj.status
      }
      else {
        this.status = 0;
      }
      if (initObj.hasOwnProperty('message')) {
        this.message = initObj.message
      }
      else {
        this.message = '';
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type MapConvertResponse
    // Serialize message field [status]
    bufferOffset = _serializer.int32(obj.status, buffer, bufferOffset);
    // Serialize message field [message]
    bufferOffset = _serializer.string(obj.message, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type MapConvertResponse
    let len;
    let data = new MapConvertResponse(null);
    // Deserialize message field [status]
    data.status = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [message]
    data.message = _deserializer.string(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.message);
    return length + 8;
  }

  static datatype() {
    // Returns string type for a service object
    return 'fastlio/MapConvertResponse';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '2c1d00fb8b4e78420f43d93d5292a429';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    int32 status
    string message
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new MapConvertResponse(null);
    if (msg.status !== undefined) {
      resolved.status = msg.status;
    }
    else {
      resolved.status = 0
    }

    if (msg.message !== undefined) {
      resolved.message = msg.message;
    }
    else {
      resolved.message = ''
    }

    return resolved;
    }
};

module.exports = {
  Request: MapConvertRequest,
  Response: MapConvertResponse,
  md5sum() { return '27938b198ec2a6b94cdc450d4db81e6d'; },
  datatype() { return 'fastlio/MapConvert'; }
};
