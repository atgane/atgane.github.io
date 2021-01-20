#include<iostream>

int com(int a, int b, int (&list)[31][31])
{
    if(b == 0 || a == b)
    {
        return 1;
    }
    if(list[a - b][b] != 0)
    {
        return list[a - b][b];
    }
    list[a - b][b] = (com(a - 1, b - 1, list) + com(a - 1, b, list));
    return list[a - b][b];
}

int main()
{
    int n;
    int a, b, memo[31][31] = {0};
    std::cin >> n;
    for(int i =  0; i < n; ++i)
    {
        std::cin >> a;
        std::cin >> b;
        std::cout << com(b, a, memo) << std::endl;
    }
}