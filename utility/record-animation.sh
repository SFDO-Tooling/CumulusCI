TMPDIR=/tmp/cci-demo
REPO=`pwd`
rm -rf $TMPDIR
mkdir $TMPDIR
cd $TMPDIR
export PS1=$ 
source $REPO/.envrc
asciinema rec -c "bash $REPO/utility/animation.sh"
