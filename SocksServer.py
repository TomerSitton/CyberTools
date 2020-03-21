from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread 
from enum import Enum
import re
from time import sleep

LOCAL_ADDR = ("0.0.0.0", 1337)

class ResponseCode(Enum):
	"""
	An Enum containing the possible response code a socks CONNECT and BIND 
	commands can have
	"""
	GRANTED = 90
	REJ_OR_FAIL = 91
	FAIL_CONN_CLI_IDENTD = 92
	REJ_DIFF_UID = 93


def try_to_connect(data):
	"""
	This function takes the data the client sent as input and tries to connect to the application the client want.
	If the connection was successful, it sends the SOCKS CONNECT GRANTED response to the client.
	the response code.
	If the connection failed, it sends the SOCKS CONNECT <reason of failure> response.
	The function returns the application socket and the response code

	:param: data - the CONNECT request the client sent
	:type: data - bytes

	:return: A tuple of the application socket (empy socket if connection not granted) and the CONNECT response code
	:rtype: tuple (socket, int)
	"""
	global ResponseCode
	response_code = ResponseCode.REJ_OR_FAIL.value
	application_port = int.from_bytes(data[2:4], 'big')
	application_ip = ".".join(str(x) for x in data[4:8])
	print("connecting to {ip}:{port}\n".format(ip=application_ip, port=application_port))
	#TODO - add address and port checking based on ident
	app_socket = socket(AF_INET, SOCK_STREAM)
	try:
		app_socket.connect((application_ip, application_port))
		response_code = ResponseCode.GRANTED.value
	except TimeoutError as t_err:
		print("could not connect to app server")
		response_code = ResponseCode.REJ_OR_FAIL.value
	finally:
		return app_socket, response_code


def create_response(response_code, ver=0, dst_port=0, dst_ip="0.0.0.0"):	
	"""
	This function creates responses for the SOCKS CONNECT/BIND commands.

	:param: response_code - the response code that needs to be sent to the client. 
			Must be a value in the ResponseCode enum
	:type: response_code - int
	:param: ver - the protocol version. defaults 0 for response
	:type: ver - int
	:param: dst_port - the destination port. defaults 0 for CONNECT response
	:tyoe: dst_port - int
	:param: dst_ip - the destination ip. defaults "0.0.0.0" for CONNECT response
	:type: dst_ip - str

	:return: bytes object to send to the client as a response
	:rtype: bytes
	"""
	ver = int.to_bytes(ver, 1, 'big')
	response_code = int.to_bytes(response_code, 1, 'big')
	dst_ip = b''.join([int.to_bytes(int(x), 1, 'big') for x in dst_ip.split(".")])
	dst_port = int.to_bytes(dst_port, 2, 'big')

	return b''.join([ver, response_code, dst_port, dst_ip, b'\x00'])


def connect_to_app(client_s):
	"""
	This function handles the connection of the socket server to the app server.
	It gets the data from the client, and if its a CONNECT request it connects to the 
	app and sends the proper response to the client.

	:param: client_s - the client's socket
	:type: client_s - socket

	:return: the application socket. Will be an empty socket if the connection was rejected/failed
	:rtype: socket
	"""
	global ResponseCode
	socks_connect_reg = re.compile("b'\\\\x0[45]\\\\x01.*\\\\x00'")

	data = client_s.recv(1024)
	if re.match(socks_connect_reg, str(data)):
		app_socket, res_code = try_to_connect(data)
		response = create_response(response_code=res_code)
		client_s.send(response)
		if res_code != ResponseCode.GRANTED.value:
			print("rejected. closing app and client sockets")
			app_socket.close()
			client_s.close()
			raise ConnectionError()
	else:
		print("excepted CONNECT request. got something else. goodbye!")
		client_s.close()
		raise ValueError()
	
	return app_socket


def bind_socks(client_s, bind_req):
	global ResponseCode
	data = bind_req
	print("binding...")
	#TODO - bind 
	

def handle_client(client_s):
	"""
	This function handles a client's connection.
	It tries to connect the client to the application he requested.
	If successful, it runs threads which tunnel the data from the client to the application
	and vice-versa.

	:param: client_s - the client's socket
	:type: client_s - socket
	"""
	try:
		app_socket = connect_to_app(client_s)
	except ConnectionError as e:
		print("the connection to the app was rejected")
		raise e
	except ValueError as e:
		print("excepted CONNECT request. got something else")
		raise e

	#socks_bind_reg = re.compile("b'\\\\x0[45]\\\\x02.*\\\\x00'")
	#if re.match(socks_bind_reg, str(data)):
	#	bind_socks(client_s, bind_req)
	
	#else:
	t1 = Thread(target=tunnel, args=(app_socket, client_s))
	t2 = Thread(target=tunnel, args=(client_s, app_socket))
	t1.start()
	t2.start()

	
		
def tunnel(src, dst):
	"""
	This function handles tunneling of data between two sockets.
	It recieves data from src socket and sends it to the dst socket.

	:param: src - the src socket. This socket sends data to the SOCKS server
	:type: src - socket
	:param: dst - the dst socket. The SOCKS server sends the data it recieved from the src socket to this socket.
	:type: dst - socket
	"""
	print("start tunneling")
	try:
		while True:
			data = src.recv(2048)
			if data != b'':
				print("REAL src({}) ==> dst({})".format(src.getpeername(), dst.getpeername()))
				print("ON SERVER src({}) ==> dst({}):\n {}\n".format(src.getsockname(), dst.getsockname(), data))
			dst.send(data)
			sleep(0.05)

	except ConnectionResetError as e:
		print("peer ({}) closed connection".format(dst.getsockname()))
	except OSError as e:
		print ("the sockets were closed. probably by and exception in the other thraed")
	except Exception as e:
		raise e
	finally:
		print("closing sockets and stoping tunnel")
		src.close()
		dst.close()
	
	

def main():
	s = socket(AF_INET, SOCK_STREAM)
	s.bind(LOCAL_ADDR)
	s.listen()
	try:
		while True:
			client_s, client_addr = s.accept()
			Thread(target=handle_client, name=client_addr[1], args=[client_s]).start()
	except Exception as e:
		raise e
	finally:
		print("closing server socket")
		s.close()


	
if __name__ == '__main__':
	main()