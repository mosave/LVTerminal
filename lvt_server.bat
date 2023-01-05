py ./lvt_server.py -c=K:\House\MultiRoom\LVTerminal\config\server_aepc.cfg

goto exit



code=42
while [ $code -eq 42 ]; do
    "$dir/lvt_server.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
    code=$?
done

:exit