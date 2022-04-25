package elements.soc.blinky

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import nafarr.blackboxes.xilinx.a7._

import zibal.misc._

import elements.sdk.ElementsApp
import elements.board.Nexys4DDR
import elements.soc.Blinky

case class Nexys4DDRBoard() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val reset = inout(Analog(Bool))
    val led = Vec(inout(Analog(Bool())), 6)
  }

  val top = Nexys4DDRTop()
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

case class Nexys4DDRTop() extends Component {
  val io = new Bundle {
    val clock = XilinxCmosIo("E3").clock(Nexys4DDR.oscillatorFrequency)
    val reset = XilinxCmosIo("C12")
    val led = Vec(
      XilinxCmosIo("H17"),
      XilinxCmosIo("K15"),
      XilinxCmosIo("J13"),
      XilinxCmosIo("N14"),
      XilinxCmosIo("R18"),
      XilinxCmosIo("V17")
    )
  }

  val soc = Blinky()

  io.clock <> IBUF(soc.io.clock)
  io.reset <> IBUF(soc.io.reset)

  for (index <- 0 until 6) {
    io.led(index) <> OBUF(soc.io.led(index))
  }
}

object Nexys4DDRPrepare extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()

    XilinxTools.Xdc(elementsConfig).generate(top.io)

    top
  }
}

object Nexys4DDRGenerate extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()

    top
  }
}

object Nexys4DDRSimulate extends ElementsApp {
  val compiled = elementsConfig.genFPGASimConfig.compile {
    val board = Nexys4DDRBoard()

    board
  }
  simType match {
    case "simulate" =>
      compiled.doSimUntilVoid("simulate") { dut =>
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 1 ms)
        testCases.addReset(dut.io.reset, 1 us)
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
