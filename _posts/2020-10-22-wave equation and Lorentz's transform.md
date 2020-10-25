---
layout: article
title: "상대성이론. 파동방정식과 광속불변성"

categories:
  상대성이론 편미분방정식 전자기학
tags:
  상대성이론 편미분방정식 전자기학
---

# 0. 소개    

(파동방정식 선이해 필요!!!)

빛은 파동이므로 파동방정식에 지배를 받는다. 파동방정식은 파동함수와 시간, 위치, 파동의 속도로 표현되는데, 이 속도를 일정하게 만든다는 것을 수학적으로 표현해보고 수식의 의미를 짚어볼 것이다.

# 1. 개요

## 1.1. 멕스웰 방정식과 빛의 속도

**목표: 진공상태의 멕스웰 방정식에서 파동방정식을 유도하자.**

멕스웰 방정식은 다음과 같다.

$$
\nabla \bullet \vec{E} = \frac{\rho}{\epsilon_0}
$$

$$
\nabla \bullet \vec{B} = 0
$$

$$
\nabla \times \vec{E} = - \frac{\partial \vec{B}} {\partial t}
$$

$$
\nabla \times \vec{B} = {\mu}_0 \left( \vec{J} + {\epsilon}_0 \frac{\partial \vec{E}} {\partial t} \right)
$$

진공의 조건에서 전하밀도와 전류밀도가 없다고 가정하면 $\rho = 0$, $\vec{J} = \vec{0}$이다. 이때 페러데이 법칙인 식$(3)$의 양 변에 회전을 적용하면 다음을 얻을 수 있다.

$$
\begin{align*}
  \nabla \times \left(\nabla \times \vec{E}\right) &= \nabla \left(\nabla \bullet \vec{E}\right) - {\nabla}^2 \vec{E} = \nabla \times \left(- \frac{\partial \vec{B}} {\partial t}\right) = - \mu_0 \epsilon_0 \frac{\partial^2 \vec{E}} {\partial t^2}    \\
  &\rightarrow {\nabla}^2 \vec{E} = \mu_0 \epsilon_0 \frac{\partial^2 \vec{E}} {\partial t^2}
\end{align*}
$$

이때 $i= 1, 2, 3$에 대하여 $E_i$가 $\vec{E}$의 $i$번째 성분이라 하고 $c = \dfrac{1} {\sqrt{\mu_0 \epsilon_0}}$라 하면 다음이 성립한다.

$$\nabla^2 E_i = \dfrac {1} {c^2} \dfrac{\partial^2 E_i} {\partial t^2}$$

3차원 파동방정식의 형태는 한편 $u$가 파동을 나타내는 함수이고 $v$가 파동의 속도일 때 다음과 같이 주어진다.

$$\nabla^2 u  = \dfrac {1} {v^2} \dfrac{\partial^2 u} {\partial t^2}$$

이 식은 위의 전기장의 형태와 유사함을 알 수 있다. 이 말은 전자기파, 즉 빛이 진공상태에서 파동의 형태로 퍼져나간다는 사실을 의미한다. 이때 $c$는 빛의 속도를 의미한다.

# 2. 파동방정식을 만족하는 좌표계의 선형변환

 기본적인 미분을 생각해보자. $y=f(x)$를 $x$로 미분했을 때

 $$dy = f'(x)dx$$

 가 성립함은 자연스럽게 알고 있는 내용이다. 또한 미분적분학에서 $z = z(x_1 ,x_2 ,\cdots)$의 전미분은 

 $$dz = \dfrac {\partial z}{\partial x_1 } dx_1  + \dfrac {\partial z}{\partial x_2 } dx_2 + \cdots$$

라는 것을 배웠을 것이다. 이를 통해 알 수 있는 사실은 $z$라는 종속변수가 $x_1 , x_2 , \cdots$라는 독립변수로 어떤 방식으로 조합되어 만들어지든 $dz$는 $dx_1 , dx_2 , \cdots$의 선형결합으로 만들 수 있다는 것이다. 비록 $dz, dx_1 ,dx_2 , \cdots$가 의미하는 바를 정확하게 알지는 못하지만 어떤 행렬 $A$에 대하여

$$\begin{pmatrix} dx_1 \\ dx_2 \\ dx_3 \\ \vdots \end{pmatrix} = A \begin{pmatrix} dx_1' \\ dx_2' \\ dx_3' \\ \vdots \end{pmatrix}$$

와 같이 선형변환의 모양으로 표현할 수 있다는 것이다. 

다시 파동방정식으로 돌아오자. 3차원 파동방정식에서 평면파가 나아가는 축을 $x$축으로 잡고 1차원 파동방정식을 고려를 하자. 이때 파동방정식은

$$\dfrac {\partial^2 E} {\partial x^2} = \dfrac{1} {c^2} \dfrac {\partial^2 E} {\partial t^2}$$

으로 구해진다. $T = ct$로 치환하면 다음과 같은 파동방정식을 얻는다. 이는 빛의 속도를 단위를 1로 바꾼거라 생각하면 된다. 

$$\dfrac {\partial^2 E} {\partial x^2} = \dfrac {\partial^2 E} {\partial T^2}$$

여기서 다음과 같은 변환을 생각하자. 

$$(T, x) \rightarrow (T', x')$$

이때 어떤 행렬 $L$가 존재하여 다음을 만족해야 함을 알 수 있다.

$$\begin{pmatrix} dT \\ dx \end{pmatrix} = L\begin{pmatrix} dT' \\ dx' \end{pmatrix}$$

우리는 이 변환을 이제 파동방정식에 집어넣어서 방정식의 꼴을 보존시키는 변환을 찾아볼 것이다. 이 말은 관성좌표계안에서 $(T, x) \rightarrow (T', x')$로 좌표변환이 일어났을 때 파동의 속도를 보존하는 좌표변환을 찾아본다는 것이고 결론으로 빛의 속도를 보존하는 변환을 찾는 것이다. 이를 식으로 표현하면 다음과 같다.

$$\dfrac {\partial^2 E} {\partial x^2} - \dfrac {\partial^2 E} {\partial T^2} = \dfrac {\partial^2 E} {\partial x'^2} - \dfrac {\partial^2 E} {\partial T'^2}$$

이제 본격적으로 행렬 $L$가 만족해야할 조건이 무엇인지 찾아보자. 우선 행렬 $L$를 다음과 같이 정의하자.

$$
\begin{align*}
L = \begin{pmatrix} A & B \\ C & D \end{pmatrix}
\end{align*}
$$

이때 식$(13)$을 전미분 공식을 이용하여 풀어쓰면 다음과 같다.

$$dT = AdT' + Bdx' = \dfrac {\partial T} {\partial T'}dT' + \dfrac {\partial T} {\partial x'}dx'$$

$$dx = CdT' + Ddx' = \dfrac {\partial x} {\partial T'}dT' + \dfrac {\partial x} {\partial x'}dx'$$

따라서 다음의 규칙을 얻는다.

$$L = \begin{pmatrix} A & B \\ C & D \end{pmatrix}= \begin{pmatrix} \dfrac {\partial T} {\partial T'} & \dfrac {\partial T} {\partial x'} \\ \dfrac {\partial x} {\partial T'} & \dfrac {\partial x} {\partial x'} \end{pmatrix}$$

$$
\dfrac {\partial} {\partial T'} = \dfrac {\partial T} {\partial T'}\dfrac {\partial } {\partial T} + \dfrac {\partial x} {\partial T'}\dfrac {\partial } {\partial x} = A\dfrac {\partial } {\partial T} + C\dfrac {\partial } {\partial x}
$$

$$
\dfrac {\partial} {\partial x'} = \dfrac {\partial T} {\partial x'}\dfrac {\partial } {\partial T} + \dfrac {\partial x} {\partial x'}\dfrac {\partial } {\partial x} = B\dfrac {\partial } {\partial T} + D\dfrac {\partial } {\partial x}
$$

$$
\dfrac {\partial^2} {\partial {T'}^2} = A^2 \dfrac {\partial^2 } {\partial T^2 } + AC \dfrac {\partial^2 } {\partial T \partial x} + AC \dfrac {\partial^2 } {\partial x \partial T} + C^2 \dfrac {\partial^2 } {\partial x^2}
$$

$$
\dfrac {\partial^2} {\partial {x'}^2} = B^2 \dfrac {\partial^2 } {\partial T^2 } + BD \dfrac {\partial^2 } {\partial T \partial x} + BD \dfrac {\partial^2 } {\partial x \partial T} + D^2 \dfrac {\partial^2 } {\partial x^2}
$$

이제 식$(20)$, 식$(21)$을 식$(14)$에 대입하면 다음의 결과를 얻는다. 

$$\dfrac {\partial^2 E} {\partial x^2} - \dfrac {\partial^2 E} {\partial T^2} =  \left(B^2 - A^2\right) \dfrac {\partial^2 } {\partial T^2 } + \left(BD - AC\right) \dfrac {\partial^2 } {\partial T \partial x} + \left(BD - AC\right) \dfrac {\partial^2 } {\partial x \partial T} + \left(D^2 - C^2 \right) \dfrac {\partial^2 } {\partial x^2}
$$

$$\dfrac {\partial^2 E} {\partial x'^2} - \dfrac {\partial^2 E} {\partial T'^2}$$

$$
\begin{align*}
  \dfrac {\partial^2 E} {\partial x^2} - \dfrac {\partial^2 E} {\partial T^2} &=  \left(B^2 - A^2\right) \dfrac {\partial^2 } {\partial T^2 } + \left(BD - AC\right) \dfrac {\partial^2 } {\partial T \partial x} + \left(BD - AC\right) \dfrac {\partial^2 } {\partial x \partial T} + \left(D^2 - C^2 \right) \dfrac {\partial^2 } {\partial x^2}    \\
  &=\dfrac {\partial^2 E} {\partial x'^2} - \dfrac {\partial^2 E} {\partial T'^2}
\end{align*}
$$

이때 각각의 항을 정리하여 빼면 다음이 성립한다.

$$B^2 - A^2 = 0$$

$$BD- AC = 0$$

$$D^2 - C^2 = 0$$