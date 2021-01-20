#include<iostream>
#include<algorithm>
int main()
{
    int n, k, w[100] = {0}, v[100] = {0}, memo[101][100001] = {0};
    std::cout << "1\n";
    std::cin >> n;
    std::cin >> k;
    std::cout << "1\n";
    for(int i = 0; i < n; ++i)
    {
        std::cin >> w[i];
        std::cin >> v[i];
    }
    for(int i = 0; i < n; ++i)
    {
        for(int j = 0; j < k; ++j)
        {
            if(j - w[i] > 0)
            {
                memo[i + 1][j + 1] = std::max(std::max(memo[i + 1][j], memo[i][j + 1]), memo[i - 1][j - w[i]] + v[i]);
            }
            else
            {
                memo[i + 1][j + 1] = std::max(memo[i + 1][j], memo[i][j + 1]);
            }
        }
    }
    for(int i = 0; i < n; ++i)
    {
        for(int j = 0; j < k; ++j)
        {
            std::cout << memo[i + 1][j + 1] << " ";
        }
        std::cout << std::endl;
    }
}