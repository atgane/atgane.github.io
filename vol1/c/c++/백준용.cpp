#include<stdio.h>
#include<stdlib.h>

int main()
{
    int* p;
    int i, hap = 0;
    int cnt;

    printf("입력할 개수는? \n");
    scanf("%d", &cnt);

    p = (int*)malloc(sizeof(int) * cnt);

    for(i = 0; i < cnt; i++)
    {
        printf("%d 번째 숫자:", i + 1);
        scanf("%d", p + i);
    }

    for(i = 0; i < cnt; i++)
        hap = hap + *(p + i);
    
    printf("입력 숫자 합 ==> %d\n", hap);
    free(p);
}