#include<iostream>
int max(int (&arr)[2])
{
    if(arr[0] > arr[1])
    {return arr[0];}
    else
    {return arr[1];}
    
}

void copy(int (&arr1)[2], int (&arr2)[2])
{
    for(int i = 0; i < 2; ++i)
    {
        arr1[i] = arr2[i];
    }
}

int main()
{
    int n;
    std::cin >> n;
    int inp;
    int rem[2]; int memo1[2] = {0}; int memo2[2] = {0};

    std::cin >> inp;
    memo2[0] = inp;
    memo2[1] = inp;

    for(int i = 0; i < n - 1; ++i)
    {
        std::cin >> inp;
        rem[0] = max(memo1) + inp;
        rem[1] = memo2[0] + inp;
        copy(memo1, memo2);
        copy(memo2, rem);
    }
    std::cout << max(memo2);
    return 0;
}