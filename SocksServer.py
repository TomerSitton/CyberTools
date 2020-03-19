from socket import socket
from threading import Thread 


LOCAL_ADDR = ("0.0.0.0", 1337)


def try_to_connect(data):
	"""
	"""
	application_port = int.from_bytes(data[2:4], 'big')
	application_ip = ".".join(str(x) for x in data[4:8])
	print(application_port)
	print(application_ip)

def __init_local_socket__(bind_addr):
	"""
	"""
	s = socket()
	s.bind(bind_addr)
	return s


def handle_requests(client_s, client_addr):
	"""
	"""
	while True:
		data = client_s.recv(1024)
		print(data)
		if data.startswith(b'\x04\x01'):
			print("this is a CONNECT request!")
			try_to_connect(data)




def main():
	s = __init_local_socket__(LOCAL_ADDR)

	try:
		while True:
			s.listen()
			client_s, client_addr = s.accept()
			Thread(target=handle_requests, name=client_addr[1], args=(client_s, client_addr)).start()
	except Exception as e:
		raise e
	finally:
		print("closing server socket")
		s.close()


	


if __name__ == '__main__':
	main()