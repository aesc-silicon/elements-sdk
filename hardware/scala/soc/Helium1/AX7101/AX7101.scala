package elements.soc.helium1

import spinal.core._
import spinal.core.sim._
import spinal.lib._

import nafarr.system.reset._
import nafarr.system.reset.ResetControllerCtrl._
import nafarr.system.clock._
import nafarr.system.clock.ClockControllerCtrl._
import nafarr.blackboxes.xilinx.a7._

import zibal.misc._
import zibal.platform.Helium
import zibal.board.{KitParameter, BoardParameter}

import elements.sdk.ElementsApp
import elements.board.AX7101
import elements.soc.Helium1

case class AX7101Board() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val uartStd = new Bundle {
      val txd = inout(Analog(Bool))
      val rxd = inout(Analog(Bool))
    }
    val gpioStatus = Vec(inout(Analog(Bool())), 4)
  }

  val top = AX7101Top()
  val analogFalse = Analog(Bool)
  analogFalse := False
  val analogTrue = Analog(Bool)
  analogTrue := True

  top.io.clockPos.PAD := io.clock
  top.io.clockNeg.PAD := False

  top.io.uartStd.rxd.PAD := io.uartStd.rxd
  io.uartStd.txd := top.io.uartStd.txd.PAD

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

case class AX7101Top() extends Component {
  val resets = List[ResetParameter](ResetParameter("system", 64), ResetParameter("debug", 64))
  val clocks = List[ClockParameter](
    ClockParameter("system", 105 MHz, "system"),
    ClockParameter("debug", 105 MHz, "debug", synchronousWith = "system")
  )

  val kitParameter = KitParameter(resets, clocks)
  val boardParameter = AX7101.Parameter(kitParameter)
  val socParameter = Helium1.Parameter(boardParameter)
  val parameter = Helium.Parameter(
    socParameter,
    128 kB,
    (resetCtrl: ResetControllerCtrl, _, clock: Bool) => { resetCtrl.buildXilinx(clock) },
    (clockCtrl: ClockControllerCtrl, resetCtrl: ResetControllerCtrl, clock: Bool) => {
      clockCtrl.buildXilinxPll(
        clock,
        boardParameter.getOscillatorFrequency,
        List("system", "debug"),
        5
      )
    }
  )

  val io = new Bundle {
    val clockPos = XilinxLvdsInput
      .Pos("R4")
      .clock(boardParameter.getOscillatorFrequency)
      .ioStandard("DIFF_SSTL15")
    val clockNeg = XilinxLvdsInput.Neg("T4").ioStandard("DIFF_SSTL15")
    val uartStd = new Bundle {
      val txd = XilinxCmosIo("AB15")
      val rxd = XilinxCmosIo("AA15")
    }
    val gpioStatus = Vec(
      XilinxCmosIo("W5").ioStandard("LVCMOS15"),
      XilinxCmosIo("E17"),
      XilinxCmosIo("F16"),
      XilinxCmosIo("T6").ioStandard("LVCMOS15")
    )
  }

  val soc = Helium1(parameter)

  val clockBuf = IBUFDS(soc.io_plat.clock)
  io.clockPos <> clockBuf
  io.clockNeg <> clockBuf

  soc.io_plat.jtag.tms := False
  soc.io_plat.jtag.tdi := False
  soc.io_plat.jtag.tck := False

  io.uartStd.txd <> OBUF(soc.io_per.uartStd.txd)
  io.uartStd.rxd <> IBUF(soc.io_per.uartStd.rxd)
  soc.io_per.uartStd.cts := False

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> IOBUF(soc.io_per.gpioStatus.pins(index))
  }
}

object AX7101Prepare extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = AX7101Top()

    top.soc.prepareZephyr("zephyr0", elementsConfig)

    val xdc = XilinxTools.Xdc(elementsConfig)
    top.soc.clockCtrl.generatedClocks foreach { clock => xdc.addGeneratedClock(clock) }
    xdc.generate(top.io)

    val embench = EmbenchIotTools(elementsConfig)
    embench.generate(top.soc.clockCtrl.getClockDomainByName("system").frequency.getValue)

    top
  }
}

object AX7101Generate extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = AX7101Top()
    top.soc.initOnChipRam(elementsConfig.swStorageZephyrBinary("zephyr0"))
    top
  }
}

object AX7101Simulate extends ElementsApp {
  val compiled = elementsConfig.genFPGASimConfig.compile {
    val board = AX7101Board()
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
        testCases.addClock(dut.io.clock, AX7101.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "boot" =>
      compiled.doSimUntilVoid("boot") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, AX7101.oscillatorFrequency, 10 ms)
        testCases.boot(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "mtimer" =>
      compiled.doSimUntilVoid("mtimer") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, AX7101.oscillatorFrequency, 400 ms)
        testCases.heartbeat(dut.io.gpioStatus(0))
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
