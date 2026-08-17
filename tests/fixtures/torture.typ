#import "template-star.typ": *
#show: project.with(title: "Torture", authors: ("parity",), date: none)

= Alpha
#def[A holomorphic thing is a thing.]
#thm(title: [Rouché's Theorem], star: true)[Suppose the hypotheses hold. Then the conclusion holds.]
#proof[By hypothesis, the claim holds. A direct computation gives $ z_1 + z_2 = z_2 + z_1 $. Therefore the conclusion holds.]
#remark(star: true)[Nasty escaping: 5 \# \$ \[ \] \{ \} \@ \* \_ \` \< \> \~ 1/2 /\/ end.]
#claim[The converse of @thm-1.2 is false: a witness exists.]
#notation[One writes x = (x, 0).]
#lem[A small stepping stone.]
= Beta
#prop[Counter reset check: expect 2.1.]
#cor[Follows from the proposition. Long body. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. Pagination filler sentence. ]
= Gamma
#axiom(star: true)[A starting point.]
#thm[Back-reference check: see @thm-1.2 and forward none.]
