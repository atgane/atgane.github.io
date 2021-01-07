#include<iostream>
int max(int a, int b)
{
    if(a > b)
    {return a;}
    else
    {return b;}
}
int main(void)
{
    int n, memo[10001] = {0};
    std::cin >> n;
    int ram1, ram2;
    for(int i = 1; i <= n; ++i)
    {
        if(i == 1)
        {
            std::cin >> ram2;
            memo[i] = ram2;
        }
        else if(i == 2)
        {
            ram1 = ram2;
            std::cin >> ram2;
            memo[i] = ram1 + ram2;
        }
        else
        {
            ram1 = ram2;
            std::cin >> ram2;
            memo[i] = max(memo[i - 1], max(memo[i - 2] + ram2, memo[i - 3] + ram1 + ram2));
        }
    }
    std::cout << memo[n];
}