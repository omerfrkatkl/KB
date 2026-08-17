#import "template-star.typ": *
#show: project.with(title: "Complex Analysis — Rule-Compliant Slice",
  authors: ("KB pipeline · vertical slice",), date: "3 May 2026 lecture")

= Regions in the Complex Plane

#def(star: true)[A set $S$ is *connected* if it cannot be expressed as the union of two disjoint nonempty open sets.]

#def(star: true)[A *domain* is a nonempty open connected set.]

#prop(star: true)[Assume that $D$ is a domain and $z_1, z_2 in D$. Then there is a polygonal path from $z_1$ to $z_2$ lying in $D$.]

= Harmonic Functions

#def(star: true)[Let $D$ be a domain. A function $u(x, y)$ is *harmonic* on $D$ if it has continuous partial derivatives of the first and second order in $D$ and satisfies Laplace's equation in $D$.]

#def(star: true)[*Laplace's equation* is the equation $nabla^2 u = 0$.]

#thm(star: true)[Assume that $f(z) = u(x, y) + i v(x, y)$ is analytic in a domain $D$. Then $u$ and $v$ are harmonic in $D$.]
#proof[Assume that $f(z) = u(x, y) + i v(x, y)$ is analytic in a domain $D$. Then $u$ and $v$ have continuous partial derivatives of all orders in $D$. Then $u_x = v_y$ and $u_y = -v_x$ in $D$. Then $u_(x x) = v_(y x)$ and $u_(y y) = -v_(x y)$, by direct computation. Then $v_(x y) = v_(y x)$. Then $u$ is harmonic in $D$. Then $v$ is harmonic in $D$. Hence $u$ and $v$ are harmonic in $D$.]

#def(star: true)[Let $u$ and $v$ be functions on a domain $D$. The function $v$ is *harmonic conjugate* of $u$ in $D$ if $u$ and $v$ are harmonic in $D$ and their first-order partial derivatives satisfy the Cauchy–Riemann equations $u_x = v_y$ and $u_y = -v_x$.]

#thm(star: true)[Assume that $f(z) = u(x, y) + i v(x, y)$ is defined on a domain $D$. Then $f$ is analytic in $D$ if and only if $v$ is a harmonic conjugate of $u$ in $D$.]
#proof[Assume that $f(z) = u(x, y) + i v(x, y)$ is defined on a domain $D$. $(=>)$ Therefore $u$ and $v$ are harmonic in $D$, by the fact that the real and imaginary parts of an analytic function are harmonic in its domain. Then the Cauchy–Riemann equations hold in $D$. Therefore $v$ is a harmonic conjugate of $u$ in $D$. $(arrow.l.double)$ Then $f$ is analytic in $D$. Hence $f$ is analytic in $D$ if and only if $v$ is a harmonic conjugate of $u$ in $D$.]

#claim(star: true)[Being a harmonic conjugate is not a symmetric relation: there exist $u, v$ such that $v$ is a harmonic conjugate of $u$ but $u$ is not a harmonic conjugate of $v$.]
#proof[Construct the pair $u = x^2 - y^2$, $v = 2 x y$ explicitly. Then $v$ is a harmonic conjugate of $u$ in $CC$. Then $g = 2 x y + i(x^2 - y^2)$ fails the Cauchy–Riemann equations off the origin, by direct computation. Therefore $g$ is not analytic in any domain, by the fact that a function is analytic in a domain if and only if its imaginary part is a harmonic conjugate of its real part there. Hence the relation is not symmetric.]

#prop(star: true)[Assume that $u$ is harmonic in a simply connected domain $D$. Then $u$ has a harmonic conjugate in $D$.]

#claim(star: true)[There exist a domain $D$ and a function $u$ harmonic in $D$ such that $u$ has no harmonic conjugate in $D$.]

#thm(star: true)[Assume that $v_1$ and $v_2$ are harmonic conjugates of $u$ in a domain $D$. Then $v_1 - v_2$ is constant in $D$.]
#proof[Assume that $v_1$ and $v_2$ are harmonic conjugates of $u$ in a domain $D$. Therefore $(v_1)_y = u_x = (v_2)_y$ and $(v_1)_x = -u_y = (v_2)_x$, by the definition of harmonic conjugate. Then $nabla (v_1 - v_2) = 0$ in $D$, by direct computation. Then $v_1 - v_2$ is constant in $D$. Hence the two conjugates differ by a constant.]

#thm(star: true)[Assume that $f = u + i v$ is analytic in a domain $D$ and $z_0 in D$ and $f'(z_0) != 0$. Then the level curves $u(x, y) = c_1$ and $v(x, y) = c_2$ through $z_0$ intersect orthogonally at $z_0$.]
#proof[Assume that $f = u + i v$ is analytic in a domain $D$ and $z_0 in D$ and $f'(z_0) != 0$. Then $nabla u dot nabla v = u_x v_x + u_y v_y$, by direct computation. Then $nabla u dot nabla v = u_x (-u_y) + u_y u_x = 0$. Then $nabla u (z_0) != 0$ and $nabla v (z_0) != 0$, and both level curves are smooth at $z_0$ with normal vectors $nabla u (z_0)$ and $nabla v (z_0)$. Then the normal vectors are orthogonal at $z_0$. Hence the level curves intersect orthogonally at $z_0$.]

#thm(star: true)[Assume that $u$ is harmonic in a domain $D$ and $z_0 in D$. Then $u(z_0) = 1/(2 pi) integral_0^(2 pi) u(z_0 + r e^(i theta)) dif theta$ for all sufficiently small $r > 0$.]
