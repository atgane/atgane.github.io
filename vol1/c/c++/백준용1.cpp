#include<cstdlib>
#include<iostream>
long long sum(long long (&_arr)[9])
{
    long long ret = 0;
    for(long long i = 0; i < 9; ++i)
    {
        ret += _arr[i];
    }
    return ret;
}

void copy(long long (&_arr1)[9], long long (&_arr2)[9])
{
    for(long long i = 0; i < 9; ++i)
    {
        _arr1[i] = _arr2[i];
    }
}

int main()
{
    long long memo1[9] = {0}; long long memo2[9]; long long ram1[9];
    long long n;
    std::cin >> n;
    for(long long i = 0; i < 9; ++i)
    {
        memo2[i] = 1;
    }

    for(long long j = 0; j < n - 1; ++j)
    {
        copy(ram1, memo2);
        for(long long i = 0; i < 9; ++i)
        {
            if(i == 0 && j == 0)
            {
                memo2[i] =ram1[1] + memo1[0] + 1;
            }
            else if(i == 0)
            {
                memo2[i] = ram1[1] + memo1[0];
            } 
            else if(i == 8)
            {
                memo2[i] = ram1[7];
            }
            else
            {
                memo2[i] = ram1[i - 1] + ram1[i + 1];
            }
            memo2[i] = memo2[i] % 1000000000;
        }
        copy(memo1, ram1);
    }
    std::cout << sum(memo2) % 1000000000;
    return 0;
}