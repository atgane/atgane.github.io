#include<iostream>
using namespace std;
uint64_t m[101] = {0, 1, 1, 1, 2, 2, 3};
uint64_t num;

uint64_t fib_seq(uint64_t n)
{
    if(n <= 6)
    {
        return m[n];
    }
    else if(m[n] != 0)
    {
        return m[n];
    }
    m[n] = fib_seq(n - 1) + fib_seq(n - 5);
    return m[n];
}

int main()
{
    cin >> num;
    for(int i = 0; i < num; ++i)
    {
        int n;
        cin >> n;
        cout << fib_seq(n) << endl;
    }
    return 0;
}