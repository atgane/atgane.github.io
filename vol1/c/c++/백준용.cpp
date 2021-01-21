#include<iostream>
int main()
{
    int n, memo1 = 0, memo2 = 0, ram = 0;
    std::cin >> n;
    for(int i = 0; i < n; ++i)
    {
        if(i == 0)
        {
            memo2 = 1;
        }
        else if(i == 1)
        {
            memo2 = 3;
            memo1 = 1;
        }
        else
        {
            ram = memo2 + 2 * memo1;
            ram %= 10007;
            memo1 = memo2;
            memo2 = ram;
        }
    }
    std::cout << memo2;
}