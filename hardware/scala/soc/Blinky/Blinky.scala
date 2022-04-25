package elements.soc

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import zibal.misc._

object Blinky {
  def apply() = Blinky()

  case class Io() extends Bundle {
    val clock = in Bool ()
    val reset = in Bool ()
    val led = out Bits (6 bits)
  }

  case class Blinky() extends Component {
    val io = Io()

    val systemClockDomain = ClockDomain(
      clock = io.clock,
      reset = io.reset,
      frequency = FixedFrequency(100 MHz),
      config = ClockDomainConfig(
        resetKind = spinal.core.SYNC,
        resetActiveLevel = LOW
      )
    )

    val logic = new ClockingArea(systemClockDomain) {
      val tick = False
      val counter = Reg(UInt(27 bits)) init (0)
      when(counter === U(100000000)) {
        counter := 0
        tick := True
      } otherwise {
        counter := counter + 1
      }

      val output = Reg(UInt(6 bits)) init (0)
      when(tick) {
        output := output + 1
      }
      io.led := output.asBits
    }
  }
}
