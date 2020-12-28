#include<iostream>
#include<vector>
#include<algorithm>
using namespace std;
int n;
vector<int> arr;
vector<int>::iterator it_arr;
vector<int> rep;
int op[4] = {0};

int bi_calc(int _x, int _y, int _a)
{
    if(_a == 0)
    {
        return _x + _y;
    }
    else if(_a == 1)
    {
        return _x - _y;
    }
    else if(_a == 2)
    {
        return _x * _y;
    }
    else
    {
        return _x / _y;
    }
    
}

void calc(int _n, int v)
{
    if(_n == n - 1)
    {
        rep.push_back(v);
    }
    else
    {
        int ret;
        for(int i = 0; i < 4; ++i)
        {
            if(op[i] >= 1)
            {
                op[i] -= 1;
                ret = bi_calc(v, it_arr[_n + 1], i);
                calc(_n + 1, ret);
                op[i] += 1;
            }
        }
    }
}

int main()
{
    cin >> n;
    for(int i = 0; i < n; ++i)
    {
        int e;
        cin >> e;
        arr.push_back(e);
    }
    for(int i = 0; i < 4; ++i)
    {
        cin >> op[i];
    }
    it_arr = arr.begin();
    calc(0, it_arr[0]);
    int min = *min_element(rep.begin(), rep.end());
    int max = *max_element(rep.begin(), rep.end());
    cout << max << endl;
    cout << min << endl;
    return 0;
}