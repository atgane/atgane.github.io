#include<iostream>
int eu(int a, int b)
{
    int r = a % b;
    if(r == 0)
    {return b;}
    else
    {return eu(b, r);}
}
int main()
{
    int n;
    std::cin >> n;
    for(int i = 0; i < n; ++i)
    {
        int x, y;
        std::cin >> x;
        std::cin >> y;
        int g = eu(x, y);
        std::cout << x * y / g << "\n";
    }
    return 0;
}