#include <iostream>
#include <vector>
using namespace std;


int main(){

    vector<int> v;

    v.push_back(10);
    v.push_back(20);
    v.push_back(30); 
    v.push_back(40);
    vector<int>::iterator iter=v.begin(); 
    v.push_back(50);
 // 벡터 반복자 시작지점

    cout << iter[3] << endl;  // 임의접근


    // 반복
    for (iter = v.begin(); iter != v.end(); ++iter){
        cout << *iter << endl;
    }

    return 0;
}