# Remastering custom golden images based on Ubuntu PRO

Vendors who wish to provide custom images based on Ubuntu PRO images can
follow the procedure below:

* Launch the Ubuntu PRO golden image
* Customize your golden image as you see fit
* If `ua status` shows attached, remove the UA artifacts to allow clean
  auto-attach on subsequent cloned VM launches
```bash
sudo ua detach
sudo rm -rf /var/log/ubuntu-advantage.log  # to remove credentials and tokens from logs
```
* Remove `cloud-init` first boot artifacts so the cloned VM boot is seen as a first boot
```bash
sudo cloud-init clean --logs
sudo shutdown -h now
```
* Use your cloud platform to clone or snapshot this VM as a golden image
