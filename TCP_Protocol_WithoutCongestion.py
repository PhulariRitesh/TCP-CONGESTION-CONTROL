# SimPy models for rdt_Sender and rdt_Receiver
# implementing the Go-Back-N Protocol

# Authors: Ritesh Phulari 2203125 , Sahil Garg 2203127,Harshil Patel 2203123,Shreeraj Deshmukh 2203130


import simpy
import random
import sys
from Packet import Packet



class rdt_Sender(object):
	
	def __init__(self,env):
		
		# Initialize variables and parameters
		self.env=env 
		self.channel=None
		
		# some default parameter values
		self.data_packet_length=10 # bits
		self.timeout_value=10 # default timeout value for the sender
		self.N=5 # Sender's Window size
		self.K=16 # Packet Sequence numbers can range from 0 to K-1
		self.cwnd = self.data_packet_length

		# some state variables and parameters for the Go-Back-N Protocol
		self.sendbase=1 # base of the current window 
		self.nextseqnum=1 # next sequence number
		self.sndpkt = {} # a buffer for storing the packets to be sent (implemented as a Python dictionary)

		# some other variables to maintain sender-side statistics
		self.total_packets_sent=0
		self.num_retransmissions=0

		
		# timer-related variables
		self.timer_is_running=False
		self.timer=None

			
	
	def rdt_send(self,msg):
		# This function is called by the 
		# sending application.
			
		# check if the nextseqnum lies within the 
		# range of sequence numbers in the current window.
		# If it does, make a packet and send it,
		# else, refuse this data.

				
		if(self.nextseqnum -1 - self.sendbase-1 <= self.cwnd):
			print("TIME:",self.env.now,"RDT_SENDER: rdt_send() called for nextseqnum=",self.nextseqnum," within current window. Sending new packet.")
			# create a new packet and store a copy of it in the buffer
			self.sndpkt[self.nextseqnum]= Packet(seq_num=self.nextseqnum, payload=msg, packet_length=self.data_packet_length)
			# send the packet
			self.channel.udt_send(self.sndpkt[self.nextseqnum])
			self.total_packets_sent+=1
			
			# start the timer if required
			if(self.sendbase==self.nextseqnum):
				self.start_timer()
			# update the nextseqnum
			self.nextseqnum = self.nextseqnum+self.data_packet_length
			return True
		else:
			print("TIME:",self.env.now,"RDT_SENDER: rdt_send() called for nextseqnum=",self.nextseqnum," outside the current window. Refusing data.")
			return False
		
	
	def rdt_rcv(self,packt):
		# This function is called by the lower-layer 
		# when an ACK packet arrives
		
		if (packt.corrupted==False):
			
			
			# check if we got an ACK for a packet within the current window.
			if(packt.seq_num-self.data_packet_length in self.sndpkt.keys()):
				
				# Since this is a cumulative acknowledgement,
				# all unacknowledged packets that were sent so far up-to 
				# the acknowledged sequence number can be treated as already acked, 
				# and removed from the buffer.
				
				while (self.sendbase!=packt.seq_num-self.data_packet_length):
					# remove packet from buffer
					# and slide the window right
					del self.sndpkt[self.sendbase]
					self.sendbase = self.sendbase + self.data_packet_length

				assert(self.sendbase==packt.seq_num-self.data_packet_length)
				# remove the acked packet from buffer
				# and slide the window right
				del self.sndpkt[self.sendbase]
				self.sendbase = self.sendbase + self.data_packet_length
				
				# if there are no more packets to be acked, stop the timer.
				if(self.sendbase==self.nextseqnum):
					self.stop_timer() # no more pending ACKs. Just stop the timer.
				else:
					self.restart_timer() # restart the timer, for a pending ACK of packet at base
				
				# exit the while loop
				print("TIME:", self.env.now, "RDT_SENDER: Got an ACK", packt.seq_num, ". Updated window Size:", self.cwnd, "base =", self.sendbase, "nextseqnum =", self.nextseqnum)
			else:
				print("TIME:",self.env.now,"RDT_SENDER: Got an ACK",packt.seq_num," for a packet in the old window. Ignoring it.")

	# Finally, these functions are used for modeling a Timer's behavior.
	def timer_behavior(self):
		try:
			# Wait for timeout 
			self.timer_is_running=True
			yield self.env.timeout(self.timeout_value)
			self.timer_is_running=False
			# take some actions 
			self.timeout_action()
		except simpy.Interrupt:
			# stop the timer
			self.timer_is_running=False

	# This function can be called to start the timer
	def start_timer(self):
		assert(self.timer_is_running==False)
		self.timer=self.env.process(self.timer_behavior())
		print("TIME:",self.env.now,"TIMER STARTED for a timeout of ",self.timeout_value)

	# This function can be called to stop the timer
	def stop_timer(self):
		assert(self.timer_is_running==True)
		self.timer.interrupt()
		print("TIME:",self.env.now,"TIMER STOPPED.")
	
	def restart_timer(self):
		# stop and start the timer
		assert(self.timer_is_running==True)
		self.timer.interrupt()
		#assert(self.timer_is_running==False)
		self.timer=self.env.process(self.timer_behavior())
		print("TIME:",self.env.now,"TIMER RESTARTED for a timeout of ",self.timeout_value)


	# Actions to be performed upon timeout
	def timeout_action(self):
		
		# re-send all the packets for which an ACK has been pending
		packets_to_be_resent = list(self.sndpkt.keys())
		print("TIME:",self.env.now,"RDT_SENDER: TIMEOUT OCCURED. Re-transmitting packets",packets_to_be_resent)
		for seq_num in packets_to_be_resent:
			self.channel.udt_send(self.sndpkt[seq_num])
			self.num_retransmissions+=1
			self.total_packets_sent+=1
		
		# Re-start the timer
		self.start_timer()
		
	# A function to print the current window position for the sender.
	def print_status(self):
		print("TIME:", self.env.now, "Current window Size:", self.cwnd, "base =", self.sendbase, "nextseqnum =", self.nextseqnum)
		
		print("---------------------")


#==========================================================================================

class rdt_Receiver(object):
	
	def __init__(self,env):
		
		# Initialize variables
		self.env=env 
		self.receiving_app=None
		self.channel=None

		# some default parameter values
		self.ack_packet_length=10 # bits
		self.K=16 # range of sequence numbers expected
		self.rcvbase=1
		#initialize state variables
		self.expectedseqnum=1
		self.sndpkt= Packet(seq_num=0, payload="ACK",packet_length=self.ack_packet_length)
		self.total_packets_sent=0
		self.num_retransmissions=0
		self.mark_rcv_receiver=[False]*100000
		self.rcvpackt = {}

		

	def rdt_rcv(self,packt):
		# This function is called by the lower-layer 
		# when a packet arrives at the receiver
		if(packt.corrupted==False):
			
			print("TIME: ",self.env.now, "RDT_RECEIVER: got packet", packt.seq_num)
			if(packt.seq_num >= self.rcvbase and not packt.seq_num in self.rcvpackt.keys()):
				self.mark_rcv_receiver[packt.seq_num] = True
				print("For ", packt.seq_num,  " marking as true")
				self.rcvpackt[packt.seq_num]=packt

			flag = True
			while(self.mark_rcv_receiver[self.rcvbase]):
				self.receiving_app.deliver_data(self.rcvpackt[self.rcvbase].payload)
				del self.rcvpackt[self.rcvbase]
				self.mark_rcv_receiver[self.rcvbase] = False
				self.rcvbase = self.rcvbase+packt.packet_length
				flag = False
				print("TIME:",self.env.now,"RDT_RECEIVER: Rcv base ", self.rcvbase)

			self.sndpkt=Packet(seq_num=self.rcvbase, payload="ACK", packet_length=self.ack_packet_length)
			self.channel.udt_send(self.sndpkt)
			if flag:
				self.num_retransmissions+=1
			self.total_packets_sent+=1
			
		else:
			# got a corrupted or unexpected packet.
			# send the ACK for the oldest packet received successfully
			if(packt.corrupted):
				print("TIME:",self.env.now,"RDT_RECEIVER: got corrupted packet",". Sent ACK",self.sndpkt.seq_num)
			else:
				print("TIME:",self.env.now,"RDT_RECEIVER: got unexpected packet with sequence number",packt.seq_num,". Sent ACK",self.sndpkt.seq_num)
			
			# send back the old ACK packet
			self.channel.udt_send(self.sndpkt)
			self.total_packets_sent+=1
			self.num_retransmissions+=1
		
