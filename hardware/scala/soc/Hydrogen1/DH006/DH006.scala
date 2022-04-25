package elements.soc.hydrogen1

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import nafarr.system.reset._
import nafarr.system.reset.ResetControllerCtrl._
import nafarr.system.clock._
import nafarr.system.clock.ClockControllerCtrl._
import nafarr.blackboxes.xilinx.a7._

import zibal.misc._
import zibal.platform.Hydrogen
import zibal.board.{KitParameter, BoardParameter}

import elements.sdk.ElementsApp
import elements.board.DH006
import elements.soc.Hydrogen1

case class DH006Board() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val jtag = new Bundle {
      val tdo = inout(Analog(Bool))
    }
    val uartStd = new Bundle {
      val txd = inout(Analog(Bool))
      val rxd = inout(Analog(Bool))
      val rts = inout(Analog(Bool))
      val cts = inout(Analog(Bool))
    }
    val gpioStatus = Vec(inout(Analog(Bool())), 4)
  }

  val top = DH006Top()
  val analogFalse = Analog(Bool)
  analogFalse := False
  val analogTrue = Analog(Bool)
  analogTrue := True

  top.io.clock.PAD := io.clock

  top.io.jtag.tms.PAD := analogFalse
  top.io.jtag.tdi.PAD := analogFalse
  io.jtag.tdo := top.io.jtag.tdo.PAD
  top.io.jtag.tck.PAD := analogFalse
  top.io.uartStd.rxd.PAD := io.uartStd.rxd
  io.uartStd.txd := top.io.uartStd.txd.PAD
  top.io.uartStd.cts.PAD := io.uartStd.cts
  io.uartStd.rts := top.io.uartStd.rts.PAD

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> top.io.gpioStatus(index).PAD
  }

  val baudPeriod = top.soc.socParameter.uartStd.init.getBaudPeriod()

  def simHook() {
    for ((domain, index) <- top.soc.parameter.getKitParameter.clocks.zipWithIndex) {
      val clockDomain = top.soc.clockCtrl.getClockDomainByName(domain.name)
      SimulationHelper.generateEndlessClock(clockDomain.clock, domain.frequency)
    }
  }
}

case class DH006Top() extends Component {
  val resets = List[ResetParameter](ResetParameter("system", 64), ResetParameter("debug", 64))
  val clocks = List[ClockParameter](
    ClockParameter("system", 90 MHz, "system"),
    ClockParameter("debug", 90 MHz, "debug", synchronousWith = "system")
  )

  val kitParameter = KitParameter(resets, clocks)
  val boardParameter = DH006.Parameter(kitParameter)
  val socParameter = Hydrogen1.Parameter(boardParameter)
  val parameter = Hydrogen.Parameter(
    socParameter,
    128 kB,
    (resetCtrl: ResetControllerCtrl, _, clock: Bool) => { resetCtrl.buildXilinx(clock) },
    (clockCtrl: ClockControllerCtrl, resetCtrl: ResetControllerCtrl, clock: Bool) => {
      clockCtrl.buildXilinxPll(
        clock,
        boardParameter.getOscillatorFrequency,
        List("system", "debug"),
        9
      )
    }
  )

  val io = new Bundle {
    val clock = XilinxCmosIo("E12").clock(boardParameter.getOscillatorFrequency)
    val jtag = new Bundle {
      val tms = XilinxCmosIo("R13")
      val tdi = XilinxCmosIo("N13")
      val tdo = XilinxCmosIo("P13")
      val tck = XilinxCmosIo("N14").clock(boardParameter.getJtagFrequency)
    }
    val uartStd = new Bundle {
      val txd = XilinxCmosIo("M4")
      val rxd = XilinxCmosIo("L4")
      val rts = XilinxCmosIo("M2")
      val cts = XilinxCmosIo("M1")
    }
    val gpioStatus =
      Vec(XilinxCmosIo("K12"), XilinxCmosIo("L13"), XilinxCmosIo("K13"), XilinxCmosIo("G11"))
  }

  val soc = Hydrogen1(parameter)

  io.clock <> IBUF(soc.io_plat.clock)

  io.jtag.tms <> IBUF(soc.io_plat.jtag.tms)
  io.jtag.tdi <> IBUF(soc.io_plat.jtag.tdi)
  io.jtag.tdo <> OBUF(soc.io_plat.jtag.tdo)
  io.jtag.tck <> IBUF(soc.io_plat.jtag.tck)

  io.uartStd.txd <> OBUF(soc.io_per.uartStd.txd)
  io.uartStd.rxd <> IBUF(soc.io_per.uartStd.rxd)
  io.uartStd.rts <> OBUF(soc.io_per.uartStd.rts)
  io.uartStd.cts <> IBUF(soc.io_per.uartStd.cts)

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> IOBUF(soc.io_per.gpioStatus.pins(index))
  }
}

object DH006Prepare extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = DH006Top()

    top.soc.prepareZephyr("zephyr0", elementsConfig)

    val xdc = XilinxTools.Xdc(elementsConfig)
    top.soc.clockCtrl.generatedClocks foreach { clock => xdc.addGeneratedClock(clock) }
    xdc.generate(top.io)

    val embench = EmbenchIotTools(elementsConfig)
    embench.generate(top.soc.clockCtrl.getClockDomainByName("system").frequency.getValue)

    top
  }
}

object DH006Generate extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = DH006Top()
    top.soc.initOnChipRam(elementsConfig.swStorageZephyrBinary("zephyr0"))
    top
  }
}

object DH006Simulate extends ElementsApp {
  val compiled = elementsConfig.genFPGASimConfig.compile {
    val board = DH006Board()
    board.top.soc.initOnChipRam(elementsConfig.swStorageZephyrBinary("zephyr0"))
    for (domain <- board.top.soc.parameter.getKitParameter.clocks) {
      board.top.soc.clockCtrl.getClockDomainByName(domain.name).clock.simPublic()
    }
    board
  }
  simType match {
    case "simulate" =>
      compiled.doSimUntilVoid("simulate") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, DH006.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "boot" =>
      compiled.doSimUntilVoid("boot") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, DH006.oscillatorFrequency, 10 ms)
        testCases.boot(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "mtimer" =>
      compiled.doSimUntilVoid("mtimer") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, DH006.oscillatorFrequency, 400 ms)
        testCases.heartbeat(dut.io.gpioStatus(0))
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
