package elements.board

import spinal.core._
import spinal.lib._

import zibal.board.{BoardParameter, KitParameter}

object DH006 {

  val oscillatorFrequency = 100 MHz

  case class Parameter(
      kitParameter: KitParameter
  ) extends BoardParameter(
        kitParameter,
        oscillatorFrequency
      ) {
    def getJtagFrequency = 10 MHz
  }
}
