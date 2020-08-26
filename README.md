This is a try to simulate basic SGs procedures of VLR for MME.
In case you don't have VLR but need to test your MME installation for voice centric UEs
and CS Fallback - this is your friend.
The program accepts SCTP connection from MME and answers four basic SGs messages initiated
by MME:
- Location Update request
- EPS detach indication
- IMSI detach indication
- MME failure
Other messages are silently ignored.

Run:
vlr.py \<host\> \<port\>  

\<host\> - IP address to listen to
\<port\> - TCP port to listen to. SGsAP default port is 29118

Run it manually or add to the systemd services:
  
$ cat /etc/systemd/system/vlr.service  
 [Unit]  
 Description=lab VLR simulator to fool MME over SGs  
 After=network.target  
 StartLimitIntervalSec=0  
 [Service]  
 Type=simple  
 Restart=always  
 RestartSec=10  
 User=user  
 ExecStart=/home/user/SGsAP/vlr.py 10.20.1.29 29118  
   
 [Install]  
 WantedBy=multi-user.target  
  
Configure VLR 10.20.1.29:29118 on your MME for CS Fallback simulation

