package elements

import zibal.misc.ElementsConfig

package object sdk {
  trait ElementsApp extends App {
    val elementsConfig = ElementsConfig(this)
    lazy val simType = if (args.length < 1) "simulate" else args(0)
  }
}
