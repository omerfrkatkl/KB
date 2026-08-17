// template.typ — Mathematics Notes Template
//
// Environment tiers:
//   Tier 1 (boxed)   — Theorem, Definition, Lemma, Proposition, Corollary,
//                       Axiom, Postulate, Conjecture
//   Tier 2 (semi)    — Claim, Recall
//   Tier 3 (light)   — Remark, Example, Notation
//   Tier 4 (plain)   — Exercise, Problem, Question, Solution, Note
//   Tier 5 (proof)   — Proof, with a QED marker
//
// All Tier 1 and Tier 2 environments share one counter, numbered as
// "section.n" (e.g. "Theorem 3.15"), and each one automatically
// receives a label matching its own displayed number — a theorem
// shown as "Theorem 3.15" gets the label <thm-3.15>, referenced with
// @thm-3.15. No manual labeling is needed, and the label always
// matches the number exactly, even if later edits shift the numbers.
//
// Trade-off: because this relies on Typst's context system, you can
// no longer attach an external label like "<my-label>" after calling
// thm[]/def[]/etc. For a memorable name on a well-known result, use
// the title: parameter instead (e.g. #thm(title: [Rouché's Theorem])[...]),
// which is purely visual and never conflicts with the automatic label.

// ═════════════════════════════════════════════════
// CONFIGURATION
// ═════════════════════════════════════════════════
#let heading-font = "Fira Sans"
#let default-author = "Ömer Faruk Atakul"

#let Re = math.op("Re")
#let Im = math.op("Im")
#let Arg = math.op("Arg")
#let Log = math.op("Log")
#let Res = math.op("Res")

// ═════════════════════════════════════════════════
// COLOR PALETTE
// ═════════════════════════════════════════════════
#let palette = (
  theorem: (accent: rgb("#B71C1C"), bg: rgb("#FFF0F0"), icon: "✦"),
  definition: (accent: rgb("#1A237E"), bg: rgb("#EDF0FA"), icon: "◆"),
  lemma: (accent: rgb("#E65100"), bg: rgb("#FFF3E0"), icon: "▸"),
  proposition: (accent: rgb("#4A148C"), bg: rgb("#F3E5F5"), icon: "◇"),
  corollary: (accent: rgb("#1B5E20"), bg: rgb("#E8F5E9"), icon: "▼"),
  axiom: (accent: rgb("#37474F"), bg: rgb("#ECEFF1"), icon: "∗"),
  postulate: (accent: rgb("#00695C"), bg: rgb("#E0F2F1"), icon: "⸬"),
  conjecture: (accent: rgb("#AD1457"), bg: rgb("#FCE4EC"), icon: "¿"),
  claim: (accent: rgb("#BF360C"), bg: none, icon: "⫧"),
  recall: (accent: rgb("#006064"), bg: none, icon: "⟲"),
  remark: (accent: rgb("#827717"), bg: none, icon: "ø"),
  example: (accent: rgb("#424242"), bg: none, icon: "⌖"),
  notation: (accent: rgb("#455A64"), bg: none, icon: "✎"),
)

#let boxed-envs = (
  "Theorem", "Definition", "Lemma", "Proposition",
  "Corollary", "Axiom", "Postulate", "Conjecture",
)

#let semi-envs = ("Claim", "Recall")

// ── exam-relevance star marker (set per item, read by the show rule) ──
#let math-env-star = state("math-env-star", false)

// ═════════════════════════════════════════════════
// TIER 1 — boxed renderer: badge header + bordered body
// ═════════════════════════════════════════════════
#let thm-box(name, number, body, title: none, accent: black, bg: white, icon: "•", star: false) = {
  v(0.6em)
  block(breakable: true, width: 100%, below: 1em, above: 0pt, {
    block(inset: 0pt, outset: 0pt, below: 0pt, above: 0pt, width: 100%, breakable: false, {
      box(
        fill: accent,
        radius: (top-left: 3pt, top-right: 3pt),
        inset: (x: 11pt, y: 5.5pt),
        text(fill: white, weight: "bold", size: 9.5pt, font: heading-font)[
          #if star [★ ]#icon #h(2pt) #smallcaps(name) #number
          #if title != none { text(fill: white, weight: "regular")[ — #title] }
        ],
      )
    })
    block(
      fill: bg,
      stroke: (
        top: 1.8pt + accent,
        bottom: 0.5pt + accent.lighten(40%),
        left: 2pt + accent.lighten(50%),
        right: none,
      ),
      inset: (x: 1.3em, top: 0.9em, bottom: 0.9em),
      radius: (bottom-left: 2pt, bottom-right: 2pt),
      width: 100%,
      above: 0pt,
      breakable: true,
      {
        set text(size: 10.5pt)
        set block(spacing: 0.65em)
        show math.equation.where(block: true): set block(breakable: false)
        body
      },
    )
  })
}

// ═════════════════════════════════════════════════
// TIER 2 — semi-formal renderer: badge header, no fill
// ═════════════════════════════════════════════════
#let semi-box(name, number, body, title: none, accent: black, icon: "•", star: false) = {
  v(0.6em)
  block(breakable: true, width: 100%, below: 1em, above: 0pt, {
    block(inset: 0pt, outset: 0pt, below: 0pt, above: 0pt, width: 100%, breakable: false, {
      box(
        fill: accent,
        radius: (top-left: 3pt, top-right: 3pt),
        inset: (x: 11pt, y: 5.5pt),
        text(fill: white, weight: "bold", size: 9.5pt, font: heading-font)[
          #if star [★ ]#icon #h(2pt) #smallcaps(name) #number
          #if title != none { text(fill: white, weight: "regular")[ — #title] }
        ],
      )
    })
    block(
      fill: none,
      stroke: (
        top: 1.8pt + accent,
        left: 2pt + accent.lighten(40%),
        bottom: 0.5pt + accent.lighten(55%),
        right: none,
      ),
      inset: (x: 1.3em, top: 0.9em, bottom: 0.9em),
      radius: (bottom-left: 2pt),
      width: 100%,
      above: 0pt,
      breakable: true,
      {
        set text(size: 10.5pt)
        set block(spacing: 0.65em)
        show math.equation.where(block: true): set block(breakable: false)
        body
      },
    )
  })
}

// ═════════════════════════════════════════════════
// TIER 3 — light renderer: left border only
// ═════════════════════════════════════════════════
#let light-box(name, number, body, title: none, accent: black, icon: "•", star: false) = {
  v(0.4em)
  block(
    inset: (left: 1.1em, top: 0.6em, bottom: 0.6em, right: 0.5em),
    stroke: (left: 3pt + accent),
    width: 100%,
    below: 1em,
    breakable: true,
    {
      text(fill: accent, weight: "bold", size: 10.5pt, font: heading-font)[#if star [★ ]#icon #h(1pt) #name]
      if number != "" {
        text(fill: accent, weight: "bold", size: 10.5pt, font: heading-font)[ #number]
      }
      if title != none {
        text(fill: accent, weight: "bold", size: 10.5pt)[ — #title]
      }
      text(fill: accent, weight: "bold")[.]
      h(0.5em)
      set text(size: 10.5pt)
      body
    },
  )
}

// ═════════════════════════════════════════════════
// DOCUMENT SETUP
// ═════════════════════════════════════════════════
#let project(
  title: "",
  authors: (default-author,),
  date: datetime.today().display("[day] [month repr:long] [year]"),
  body,
) = {
  set page(
    paper: "a4",
    margin: (x: 2.5cm, y: 2.5cm, top: 3cm, bottom: 2.5cm),
    numbering: "1",
    header: context {
      let page-num = counter(page).get().first()
      if page-num > 1 {
        set text(size: 0.85em, style: "italic", fill: luma(90), font: "Fira Sans")
        let headings = query(selector(heading).before(here()))
        let current-heading = if headings.len() > 0 { headings.last().body } else { [#title] }

        if calc.even(page-num) {
          align(left)[#title #h(1fr) #page-num]
        } else {
          align(right)[#page-num #h(1fr) #current-heading]
        }
        v(0.3em)
        line(length: 100%, stroke: 0.4pt + luma(140))
      }
    },
    footer: none,
  )

  set text(font: "Fira Sans", size: 11pt, lang: "en", region: "us")
  show math.equation: set text(font: "Fira Math")

  show heading.where(level: 1): it => {
    counter(figure.where(kind: "math-env")).update(0)
    v(2em)
    block(below: 1em, {
      text(font: heading-font, weight: "bold", size: 18pt, fill: rgb("#1a1a1a"))[
        #context {
          let nums = counter(heading).get()
          if nums.len() > 0 [#nums.first(). ]
        }
        #it.body
      ]
      v(0.4em)
      line(length: 100%, stroke: 1pt + rgb("#bbbbbb"))
    })
  }

  show heading.where(level: 2): it => {
    v(1em)
    block(below: 0.6em, {
      text(font: heading-font, weight: "bold", size: 13pt, fill: rgb("#333333"))[
        #context {
          let nums = counter(heading).get()
          if nums.len() >= 2 [#nums.at(0).#nums.at(1). ]
        }
        #it.body
      ]
    })
  }

  show heading.where(level: 3): it => {
    v(0.8em)
    block(below: 0.5em, {
      text(font: heading-font, weight: "bold", size: 11.5pt, fill: rgb("#444444"))[
        #context {
          let nums = counter(heading).get()
          if nums.len() >= 3 [#nums.at(0).#nums.at(1).#nums.at(2). ]
        }
        #it.body
      ]
    })
  }

  show raw.where(block: true): block.with(fill: luma(248), inset: 10pt, radius: 4pt, width: 100%)

  set par(justify: true, leading: 0.65em, first-line-indent: 0em)
  show link: it => text(fill: rgb("#1a237e"), it)
  set heading(numbering: "1.1")
  show figure: set align(start)
  set enum(indent: 0.8em, body-indent: 0.5em)
  set list(indent: 0.8em, body-indent: 0.5em)

  // Cross-references: read both the section and the instance counter
  // at the REFERENCED element's own location, not at the location of
  // the @reference itself — otherwise a reference to an earlier
  // section written later in the document shows the wrong number.
  show ref: it => {
    let el = it.element
    if el != none and el.func() == figure and el.kind == "math-env" {
      let supp = el.supplement.text
      if el.numbering != none {
        let loc = el.location()
        let h = counter(heading).at(loc)
        let section = if h.len() > 0 { h.first() } else { 0 }
        let n = el.counter.at(loc).first()
        let num = if section > 0 { str(section) + "." + str(n) } else { str(n) }
        link(loc, box([#supp #num]))
      } else if el.caption != none {
        link(el.location(), box([#el.caption.body]))
      } else {
        link(el.location(), box([#supp]))
      }
    } else {
      it
    }
  }

  show figure.where(kind: "math-env"): it => context {
    let starred = math-env-star.at(it.location())
    let supp = it.supplement.text
    let key = lower(supp)
    let p = if key in palette { palette.at(key) } else { palette.at("recall") }

    let number = if it.numbering != none {
      context {
        let h = counter(heading).get()
        let section = if h.len() > 0 { h.first() } else { 0 }
        let n = it.counter.get().first()
        str(section) + "." + str(n)
      }
    } else { "" }

    let env-title = if it.caption != none { it.caption.body } else { none }

    if supp in boxed-envs {
      thm-box(supp, number, it.body, title: env-title, accent: p.accent, bg: p.bg, icon: p.icon, star: starred)
    } else if supp in semi-envs {
      semi-box(supp, number, it.body, title: env-title, accent: p.accent, icon: p.icon, star: starred)
    } else {
      light-box(supp, number, it.body, title: env-title, accent: p.accent, icon: p.icon, star: starred)
    }
  }

  // Cover page + automatic outline
  if title != "" {
    set page(header: none, numbering: none)
    v(1fr)
    align(center)[
      #block(text(font: heading-font, weight: 900, size: 28pt, fill: rgb("#1a1a1a"), title))
      #v(1.5em, weak: true)
      #line(length: 40%, stroke: 1.5pt + luma(180))
      #v(1.5em, weak: true)
      #if authors.len() > 0 {
        text(size: 14pt, fill: luma(60), style: "italic", authors.join(", "))
      }
      #v(0.8em)
      #if date != none { text(size: 12pt, fill: luma(100), date) }
    ]
    v(1fr)
    pagebreak()
    counter(page).update(1)
  }

  show outline: it => {
    block(below: 1.5em)[
      #text(font: heading-font, weight: "bold", size: 18pt, fill: rgb("#1a1a1a"))[Contents]
      #v(0.3em)
      #line(length: 100%, stroke: 1.2pt + rgb("#cccccc"))
    ]
    it
  }
  show outline.entry.where(level: 1): it => { v(12pt, weak: true); strong(it) }

  outline(title: none, indent: auto)
  pagebreak()

  body
}

// ═════════════════════════════════════════════════
// MATH ENVIRONMENT NUMBERING & AUTO-LABELING
// ═════════════════════════════════════════════════
#let _title-content(title) = {
  if title == none { none }
  else if type(title) == str { eval(title, mode: "markup") }
  else { title }
}

#let math-numbering(n) = context {
  let h = counter(heading).get()
  let section = if h.len() > 0 { h.first() } else { 0 }
  if section > 0 { str(section) + "." + str(n) } else { str(n) }
}

// key (e.g. "thm", "def") builds the auto-label matching this
// environment's own displayed number — see the file header note.
#let math-item(body, title, supplement, key, nl: false, star: false) = [
  #math-env-star.update(star)#context {
    let h = counter(heading).get()
    let section = if h.len() > 0 { h.first() } else { 0 }
    let next-n = counter(figure.where(kind: "math-env")).get().first() + 1
    let lbl-str = if section > 0 {
      key + "-" + str(section) + "." + str(next-n)
    } else {
      key + "-" + str(next-n)
    }
    [#figure(
      if nl { parbreak() + body } else { body },
      kind: "math-env",
      supplement: supplement,
      caption: _title-content(title),
      numbering: math-numbering,
      outlined: false,
    )#label(lbl-str)]
  }
]

#let math-item-unnumbered(body, title, supplement, nl: false, star: false) = {
  math-env-star.update(star)
  figure(
  if nl { parbreak() + body } else { body },
  kind: "math-env",
  supplement: supplement,
  caption: _title-content(title),
  numbering: none,
  outlined: false,
  )
}

// ═════════════════════════════════════════════════
// TIER 1 — boxed environments
// ═════════════════════════════════════════════════
#let thm(body, title: none, nl: false, star: false) = math-item(body, title, "Theorem", "thm", nl: nl, star: star)
#let def(body, title: none, nl: false, star: false) = math-item(body, title, "Definition", "def", nl: nl, star: star)
#let lem(body, title: none, nl: false, star: false) = math-item(body, title, "Lemma", "lem", nl: nl, star: star)
#let prop(body, title: none, nl: false, star: false) = math-item(body, title, "Proposition", "prop", nl: nl, star: star)
#let cor(body, title: none, nl: false, star: false) = math-item(body, title, "Corollary", "cor", nl: nl, star: star)
#let axiom(body, title: none, nl: false, star: false) = math-item(body, title, "Axiom", "axiom", nl: nl, star: star)
#let postulate(body, title: none, nl: false, star: false) = math-item(body, title, "Postulate", "postulate", nl: nl, star: star)
#let conjecture(body, title: none, nl: false, star: false) = math-item(body, title, "Conjecture", "conjecture", nl: nl, star: star)
#let claim(body, title: none, nl: false, star: false) = math-item(body, title, "Claim", "claim", nl: nl, star: star)

// ═════════════════════════════════════════════════
// TIER 2 & 3 — unnumbered environments
// ═════════════════════════════════════════════════
#let recall(body, title: none, nl: false, star: false) = math-item-unnumbered(body, title, "Recall", nl: nl, star: star)
#let remark(body, title: none, nl: false, star: false) = math-item-unnumbered(body, title, "Remark", nl: nl, star: star)
#let ex(body, title: none, nl: false, star: false) = math-item-unnumbered(body, title, "Example", nl: nl, star: star)
#let notation(body, title: none, nl: false, star: false) = math-item-unnumbered(body, title, "Notation", nl: nl, star: star)

// ═════════════════════════════════════════════════
// TIER 4 — plain blocks
// ═════════════════════════════════════════════════
#let simple-block(title-text, body, nl: false) = {
  v(0.3em)
  block(below: 1em, breakable: true, inset: (left: 0.5em), {
    text(weight: "bold", fill: luma(40), size: 10.5pt)[#title-text]
    if body != none {
      text(weight: "bold", fill: luma(40))[.]
      if nl { parbreak() } else { h(0.5em) }
      body
    }
  })
}

#let que(body, title: none, nl: false) = simple-block(
  "Question" + if title != none { " (" + title + ")" }, body, nl: nl,
)
#let prob(body, title: none, nl: false) = simple-block(
  "Problem" + if title != none { " (" + title + ")" }, body, nl: nl,
)
#let exer(title: none, nl: false, ..args) = {
  let positional = args.pos()
  math-item-unnumbered(positional.at(0), title, "Exercise", nl: nl)
  if positional.len() > 1 {
    simple-block("Solution", positional.at(1), nl: nl)
  }
}
#let solution(body, nl: false) = simple-block("Solution", body, nl: nl)

#let note(body, nl: false) = {
  v(0.3em)
  block(
    fill: rgb("#F5F5F0"),
    stroke: (left: 3pt + rgb("#9E9E9E")),
    inset: (x: 1em, top: 0.6em, bottom: 0.6em),
    radius: 2pt,
    width: 100%,
    below: 1em,
    breakable: true,
    {
      text(weight: "bold", fill: rgb("#616161"), size: 10pt, font: heading-font)[▸ Note.]
      if nl { parbreak() } else { h(0.5em) }
      set text(size: 10.5pt)
      set block(spacing: 0.65em)
      body
    },
  )
}

// ═════════════════════════════════════════════════
// TIER 5 — proof, with QED marker
// ═════════════════════════════════════════════════
#let proof(body, nl: false) = {
  v(0.3em)
  block(width: 100%, inset: (left: 0.5em, top: 0.4em, bottom: 0.5em, right: 0.5em), breakable: true, {
    text(style: "italic", weight: "bold", fill: rgb("#5C6BC0"), size: 10.5pt)[Proof.]
    if nl { parbreak() } else { h(0.5em) }
    set block(spacing: 0.65em)
    body
    h(1fr)
    text(fill: rgb("#5C6BC0"))[$square.filled$]
  })
}

// ═════════════════════════════════════════════════
// HELPER — numbered display equation
// ═════════════════════════════════════════════════
#let num-eq(body) = {
  set math.equation(numbering: (..nums) => {
    let h = counter(heading).get()
    let section = if h.len() > 0 { h.first() } else { 0 }
    if section > 0 {
      "(" + str(section) + "." + str(nums.pos().first()) + ")"
    } else {
      "(" + str(nums.pos().first()) + ")"
    }
  })
  math.equation(block: true, body)
}
