import requests
from typing import Optional, Dict, Any, Union
from functools import wraps
import time
class DogControllerSDK:
    def __init__(self, base_url: str = "http://localhost:5000", robot_ip: str = "" , timeout: int = 10):
        """
        Initialize the Dog Controller SDK.
        
        Args:
            base_url: Base URL of the Dog Controller API (default: http://localhost:5000)
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url.rstrip('/')
        self.robot_ip=robot_ip
        self.timeout = timeout
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Internal method to handle all HTTP requests
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without leading slash)
            **kwargs: Additional arguments for requests.request
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: For request failures
            ValueError: For invalid JSON responses
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def connect(self) -> Dict[str, Any]:
        """
        Establish connection to the dog.
        
        Returns:
            Dictionary containing status and message from the API.
        """
        return self._make_request('POST', '/api/connect',json={"robot_ip":self.robot_ip})
    
    def euler(self,x,y,z):

        payload={
        "x":float(x),
        "y":float(y),
        "z":float(z)
        }
        return self._make_request('POST','/api/euler',json=payload)
    
    def switchGait(self,gait):

        return self._make_request('POST','/api/switchGait',json={"gait":gait})
    
    def switchMotion(self,motion):
        
        return self._make_request('POST','/api/switchMotion',json={"motion":motion})
    
    def action(self, action_code: Optional[int] = None) -> Dict[str, Any]:
        """
        Send an action command to the dog.
        
        Args:
            action_code: The action code to execute (defaults to BalanceStand)
            
        Returns:
            Dictionary containing status and message from the API.
        """
        payload = {}
        if action_code is not None:
            payload['action_code'] = action_code
        return self._make_request('POST', '/api/action', json=payload)
    
    def move(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Dict[str, Any]:
        """
        Command the dog to move.
        
        Args:
            x: Movement in x direction
            y: Movement in y direction
            z: Movement in z direction
            
        Returns:
            Dictionary containing status and message from the API.
        """
        payload = {
            'x': float(x),
            'y': float(y),
            'z': float(z)
        }
        return self._make_request('POST', '/api/move', json=payload)
    
    def close(self):
        """Close the session."""
        res=self._make_request('POST','/api/disconnect')
        self.session.close()
        return res
    
    def __enter__(self):
        """Context manager entry."""
        print(self.connect())
        if self.robot_ip=="":
            time.sleep(10)
        else:
            time.sleep(18)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the session."""
        time.sleep(5)
        print(self.close())


