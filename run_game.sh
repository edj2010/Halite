#!/bin/bash
touch out.txt
for i in `seq 1 $3`;
do
    echo $i / $3
    ./halite --replay-directory replays/ -vvv --width 32 --height 32 "python3 $1" "python3 $2" &>> out.txt
done
grep "Player 0" out.txt | grep "rank 1" | wc -l
rm out.txt
