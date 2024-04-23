# SimPy model for an unreliable communication channel.
#
#	A packet sent over this channel:
#		- can get corrupted, with probability Pc
#		- can get lost, with probability Pl
#		- reaches the other end after a "propagation_delay" amount of time, if it is not lost.
#


import simpy
import random
from Packet import Packet
import copy


class UnreliableChannel(object):

	def __init__(self,env,name,Pc,Pl,propagation_delay,transmission_rate, bandwidth):
		# Initialize variables
		self.env=env 
		self.name=name
		self.Pc=Pc
		self.Pl=Pl
		self.propagation_delay=propagation_delay
		self.transmission_rate=transmission_rate
		self.receiver=None
		
		
		self.bandwidth = bandwidth
		# some variables to maintain stats
		self.channel_utilization_time=0.0 # total amount of time for which the channel was utilized for transmission
	
	def udt_send(self,packt_to_be_sent):
		# this function is called by the sending-side 
		# to send a new packet over the channel.
		packt=copy.copy(packt_to_be_sent) #!!! BEWARE: Python uses pass-by-reference by default.Thus a copy() is necessary
		print("TIME:",self.env.now,self.name,": udt_send called for",packt)
		# start a process to deliver this packet across the channel.
		
		self.env.process(self.deliver_packet_over_channel(self.propagation_delay, packt))
		# if(cwnd > self.bandwidth):
		# 	self.Pl = 0.9
		# else:
		# 	self.Pl = 0.1
		# update stats
		transmission_delay_for_packet = packt.packet_length / self.transmission_rate
		self.channel_utilization_time += transmission_delay_for_packet
		


	def deliver_packet_over_channel(self, propagation_delay, packt_to_be_delivered):
		packt=copy.copy(packt_to_be_delivered)

		# cwnd = self.sender.cwnd
		# Pl = self.map_cwnd_to_pl(cwnd)

		
		# Is this packet corrupted?
		if random.random()<self.Pc:
			packt.corrupt()
			print("TIME:",self.env.now,self.name,":",packt,"was corrupted!")

		# Is this packet lost?
		if random.random()<self.Pl:
			print("TIME:",self.env.now,self.name,":",packt,"was lost!")
		else:
			# If the packet isn't lost, it should reach the destination.
			# Now wait for "propagation_delay" amount of time
			yield self.env.timeout(propagation_delay)
			# deliver the packet by calling the rdt_rcv()
			# function on the receiver side.
			self.receiver.rdt_rcv(packt)

	# def map_cwnd_to_pl(self, cwnd):
    # # Example mapping function: linear mapping from cwnd to Pl
	# 	min_cwnd = 3 * self.transmission_rate  # Minimum cwnd (e.g., initial cwnd)
	# 	max_cwnd = self.sender.ssthresh  # Maximum cwnd (e.g., ssthresh)
	# 	min_pl = 0.1
	# 	max_pl = 0.9
    
    # 	# Linear mapping
	# 	if cwnd <= min_cwnd:
	# 		return max_pl
	# 	elif cwnd >= max_cwnd:
	# 		return min_pl
	# 	else:
    #     	# Linear interpolation
	# 		return min_pl + (max_pl - min_pl) * (max_cwnd - cwnd) / (max_cwnd - min_cwnd)

		