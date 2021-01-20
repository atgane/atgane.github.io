#include<iostream>

int com(int a, int b, int (&list)[100][100])
{
    if(b == 0 || a == b)
    {
        return 1;
    }
    if(list[a - b][b] != 0)
    {
        return list[a - b][b];
    }
    list[a - b][b] = com(a - 1, b - 1, list) + com(a - 1, b, list) % 10007;
    return list[a - b][b];
}

int main()
{
    int a, b, memo[100][100] = {0};
    std::cin >> a;
    std::cin >> b;
    std::cout << com(a, b, memo);
}