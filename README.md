sudo /usr/pgsql-14/bin/postgresql-14-setup initdb
sudo systemctl enable postgresql-14
sudo systemctl start postgresql-14


---


[program:benedicte]
command=/home/william/benedicte_project/.venv/bin/gunicorn --workers 3 --bind unix:/run/benedicte.sock Benedicte.wsgi:application
# -- ou -- si vous préférez un port :
# command=/home/william/benedicte_project/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8001 nom_projet.wsgi:application

user=william ;
directory=/home/william/benedicte_project ; 
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/benedicte_stderr.log
stdout_logfile=/var/log/supervisor/benedicte_stdout.log
environment=LANG=en_US.UTF-8,LC_ALL=en_US.UTF-8 ; 

# Permissions pour le socket si vous utilisez un socket unix
# umask=007
# group=nginx ; ou apache, ou www-data selon votre serveur web