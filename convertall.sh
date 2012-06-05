prefix=$1
postfix=$2
let ind=10; 
for i in `ls  | grep $prefix`
do 
    let ind=$(($ind+1))
    kim_rename.sh $i $postfix$ind"_000"
done
