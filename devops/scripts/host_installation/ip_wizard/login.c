#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>

int main()
{
   if (0 == system("python3 /home/netconfig/login.py")){

      if (0 != rename("/home/netconfig/interfaces", "/etc/network/interfaces")){
        printf("rename failed\n");
        return 1;
      }

      if (0 != chown("/etc/network/interfaces", 0, 0)){
        printf("chown failed\n");
        return 1;
      }

      if (0 != chmod("/etc/network/interfaces", 0644)){
        printf("chmod failed\n");
        return 1;
      }

      printf("interfaces file updated\n");

      if (0 != rename("/home/netconfig/banner", "/etc/issue")) {
        printf("set banner failed\n");
        return 1;
      }

      system("sudo reboot");

   } else {
      printf("Keeping the network settings\n");
   }
   return 0;
}
