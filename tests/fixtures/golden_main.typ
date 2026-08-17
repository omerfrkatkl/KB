#import "template-star.typ": *
#import "symbols-gen.typ": *

#show: project.with(title: [Complex Analysis], date: none)

= Unplaced

#def[A *domain* is a non-empty open connected set.]

#def[Let $D$ be a domain. A function $u(x, y)$ is *harmonic* in $D$ if it has continuous second partials and $nabla^2 u = 0$ in $D$.]

#prop[$u_x = v_y$ and $u_y = -v_x$.]

#remark[The converse holds on a simply connected domain, as in @prop-1.3.]

#thm(title: [Harmonic Parts Theorem], star: true)[Assume that $f = u + i v$ is analytic in $D$. Then $u$ and $v$ are harmonic in $D$.]

#proof[Assume that $f = u + i v$ is analytic in $D$. Therefore $u_x = v_y$, by the fact that the Cauchy–Riemann equations hold for an analytic function. Then $u_(x x) + u_(y y) = 0$, by direct computation. Hence $u$ and $v$ are harmonic.]
