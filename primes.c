//C CODE:

#include <stdio.h>
#include <stdlib.h>

int getint() {
	int a;
	char ch;
	if(scanf("%d", &a) == 0) {
		printf("Error: cannot enter non-numeric input.\n");
		exit(1);
	} else if(scanf("%c", &ch) == EOF) {
		printf("Error: unexpected end of input.\n");
		exit(1);
	}
	return a;
}

void putint(int a) {
	printf("%d\n", a);
}

int divide(int x, int y) {
	if(y == 0) {
		printf("Error: cannot divide by 0.\n");
		exit(1);
	}
	return x / y;
}

int main() {
	int n;
	n = getint();
	int cp;
 	cp = 2;
	while (1) {
		if (!(n > 0)) break;
		int found;
		found = 0;
		int cf1;
		cf1 = 2;
		int cf1s;
		cf1s = (cf1 * cf1);
		while (1) {
			if (!(cf1s <= cp)) break;
			int cf2;
			cf2 = 2;
			int pr;
			pr = (cf1 * cf2);
			while (1) {
				if (!(pr <= cp)) break;
				if (pr == cp) {
					found = 1;
				}
				cf2 = (cf2 + 1);
				pr = (cf1 * cf2);
			}
			cf1 = (cf1 + 1);
			cf1s = (cf1 * cf1);
		}
		if (found == 0) {
			putint (cp);
			n = (n - 1);
		}
		cp = (cp + 1);
	}
}