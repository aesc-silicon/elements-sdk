package elements.soc.blinky

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import zibal.misc._

import nafarr.blackboxes.ihp.sg13s._

import elements.sdk.ElementsApp
import elements.board.Nexys4DDR
import elements.soc.Blinky

case class VirtualSG13S2Board() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val reset = inout(Analog(Bool))
    val led = Vec(inout(Analog(Bool())), 6)
  }
  val clockPeriod = 10

  val top = VirtualSG13S2Top()
  val analogFalse = Analog(Bool)
  analogFalse := False
  val analogTrue = Analog(Bool)
  analogTrue := True

  top.io.clock.PAD := io.clock
  top.io.reset.PAD := io.reset

  for (index <- 0 until 6) {
    io.led(index) <> top.io.led(index).PAD
  }
}

case class VirtualSG13S2Top() extends Component {
  val io = new Bundle {
    val clock = IhpCmosIo("top", 0)
    val reset = IhpCmosIo("top", 2)
    val led = Vec(
      IhpCmosIo("right", 0),
      IhpCmosIo("right", 2),
      IhpCmosIo("bottom", 0),
      IhpCmosIo("bottom", 2),
      IhpCmosIo("left", 0),
      IhpCmosIo("left", 2)
    )
  }

  val soc = Blinky()

  io.clock <> ixc013_i16x(soc.io.clock)
  io.reset <> ixc013_i16x(soc.io.reset)

  for (index <- 0 until 6) {
    io.led(index) <> ixc013_b16m().asOutput(soc.io.led(index))
  }
}

object VirtualSG13S2Prepare extends ElementsApp {
  elementsConfig.genASICSpinalConfig.generateVerilog {
    val top = VirtualSG13S2Top()

    val io = CadenceTools.Io(elementsConfig)
    io.addPad("top", 1, "gndpad")
    io.addPad("right", 1, "gndcore")
    io.addPad("bottom", 1, "vddcore")
    io.addPad("left", 1, "vddpad")
    io.addCorner("topright", 90, "corner")
    io.addCorner("bottomright", 0, "corner")
    io.addCorner("bottomleft", 270, "corner")
    io.addCorner("topleft", 180, "corner")
    io.generate(top.io, elementsConfig.zibalBuildPath)

    val sdc = CadenceTools.Sdc(elementsConfig)
    sdc.addClock(top.io.clock.PAD, Nexys4DDR.oscillatorFrequency)
    sdc.generate(elementsConfig.zibalBuildPath)

    top
  }
}

object VirtualSG13S2Generate extends ElementsApp {
  elementsConfig.genASICSpinalConfig.generateVerilog {
    val top = VirtualSG13S2Top()
    top
  }
}

object VirtualSG13S2Simulate extends ElementsApp {
  val compiled = elementsConfig.genASICSimConfig.compile {
    val board = VirtualSG13S2Board()
    board
  }
  simType match {
    case "simulate" =>
      compiled.doSimUntilVoid("simulate") { dut =>
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 3 ms)
        testCases.addReset(dut.io.reset, 1 us)
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
