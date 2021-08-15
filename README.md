# on_air_sign
An ON_AIR sign board with RGB LED matrix and a separate controller 


# make secret.py file
You would need to make secret.py file with following contents:

secrets = {
    'ssid' : 'yourssid', # home wifi access point ssid
    'password' : 'ssidpassword', # password for ssid
    'timezone' : "Asia/Tokyo", # http://worldtimeapi.org/timezones
    'aio_username': "aiouser", # Adafruit IO user name
    'aio_password': "aiokey", # Adafruit IO password
    'broker': "awsiotxxx.amazonaws.com", # AWS IoT Device data endpoint
    "client_id": "on_air_sign_featherm4", # AWS IoT Things name for testing
    "client_id_controller": "on_air_sign_controller", # AWS IoT Things name for controller
    "client_id_matrix": "on_air_sign_matrix", # AWS IoT Things name for matrix
}

# copy AWS IoT device certificates and private keys

Define AWS IoT Thing for controller and matrix. Download device certificates and private keys in aws folder.

aws/aws_cert_controller.pem.crt
aws/aws_cert_matrix.pem.crt
aws/private_controller.pem.key
aws/private_matrix.pem.key

# code to use Adafruit IO

code_controller.py
code_matrix.py

Copy them as code.py to controller and matrix.

# code to use AWS IoT

code_controller_aws.py
code_matrix_aws.py

Copy them as code.py to controller and matrix.
