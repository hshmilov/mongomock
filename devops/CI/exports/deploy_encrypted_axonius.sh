set -e

DECRYPT_USER=decrypt
echo "Setting $DECRYPT_USER user"
useradd $DECRYPT_USER
mkdir -p /home/$DECRYPT_USER
chown decrypt /home/$DECRYPT_USER
usermod -s /home/$DECRYPT_USER/decrypt_user.py decrypt
usermod -aG sudo $DECRYPT_USER
echo $DECRYPT_USER:decrypt | /usr/sbin/chpasswd
cp ./uploads/decrypt_wizard/decrypt_user.py /home/$DECRYPT_USER/decrypt_user.py
cp ./uploads/decrypt_wizard/first_install.py /home/$DECRYPT_USER/first_install.py
cp ./uploads/decrypt_wizard/install_and_run.sh /home/$DECRYPT_USER/install_and_run.sh
chmod +x /home/$DECRYPT_USER/install_and_run.sh
chown -R $DECRYPT_USER:$DECRYPT_USER /home/$DECRYPT_USER/
chmod 0744 /home/$DECRYPT_USER/*.py
echo "decrypt ALL=(ALL) NOPASSWD: /home/$DECRYPT_USER/first_install.py" > /etc/sudoers.d/90-decrypt
echo "Done setting user $DECRYPT_USER"

echo "$AXONIUS_VERSION_NAME" | tee /home/decrypt/version.txt
chown decrypt:decrypt /home/decrypt/version.txt
chmod 0444 /home/decrypt/version.txt
