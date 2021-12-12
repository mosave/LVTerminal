py ./lvt_client.py -c=.\config\client_mosave1.cfg

goto exit





code=42
while [ $code -eq 42 ]; do
    "$dir/lvt_server.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
    code=$?
done


:exit