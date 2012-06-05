#!/bin/bash
head=$1
to=$2
mv $head $to
cd $to
# rename
for file in `ls $head*`; do
	newf=`echo $file|sed -e s/$head/$to/`
	mv $file $newf	
done
# text files converted
for file in `ls *`; do
	textfile=`file $file|grep -i text`
	if [ -n "$textfile" ] 
	then
		# If it's a text file, try and convert
		tempfile=`mktemp`
		cat $file|sed -e s/$head/$to/ > $tempfile
		mv $tempfile $file
	fi
done
cd ..
