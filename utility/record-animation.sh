set -e
set -x
# brew install pv
# brew install asciinema

# also: VIM, git, cci in path

TMPDIR=/tmp/cci-demo
REPO=`pwd`
rm -rf $TMPDIR
mkdir $TMPDIR
cd $TMPDIR
cp $REPO/utility/animation/* $TMPDIR
git clone https://github.com/prescod/CCI-Food-Bank.git
cd CCI-Food-Bank
cci org default --unset dev
cci org scratch_delete dev
cci org scratch_delete qa
cd ..
echo "Recording script in '$TMPDIR'"
sleep 5
time asciinema rec demo.cast --idle-time-limit 2.5 --command "bash $TMPDIR/animation.sh"
