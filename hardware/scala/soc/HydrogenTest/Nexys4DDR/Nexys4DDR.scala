package elements.soc.hydrogentest

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
import elements.board.Nexys4DDR
import elements.soc.HydrogenTest

case class Nexys4DDRBoard() extends Component {
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
    val spiA = new Bundle {
      val ss = inout(Analog(Bool))
      val sclk = inout(Analog(Bool))
      val mosi = inout(Analog(Bool))
    }
    val gpioA = Vec(inout(Analog(Bool())), 32)
    val freqCounterA = inout(Analog(Bool))
    val pioA = Vec(inout(Analog(Bool())), 1)
  }

  val top = Nexys4DDRTop()
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

  io.spiA.ss := top.io.spiA.ss.PAD
  io.spiA.sclk := top.io.spiA.sclk.PAD
  io.spiA.mosi := top.io.spiA.mosi.PAD
  top.io.spiA.miso.PAD := analogFalse
  top.io.i2cA.scl.PAD := analogFalse
  top.io.i2cA.sda.PAD := analogFalse
  top.io.freqCounterA.PAD := io.freqCounterA

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> top.io.gpioStatus(index).PAD
  }

  for (index <- 0 until 32) {
    io.gpioA(index) <> top.io.gpioA(index).PAD
  }
  top.io.gpioA(1).PAD := analogTrue

  for (index <- 0 until 1) {
    io.pioA(index) <> top.io.pioA(index).PAD
  }
  top.io.pioA(1).PAD := analogTrue

  val baudPeriod = top.soc.socParameter.uartStd.init.getBaudPeriod()

  def simHook() {
    for ((domain, index) <- top.soc.parameter.getKitParameter.clocks.zipWithIndex) {
      val clockDomain = top.soc.clockCtrl.getClockDomainByName(domain.name)
      SimulationHelper.generateEndlessClock(clockDomain.clock, domain.frequency)
    }
  }
}

case class Nexys4DDRTop() extends Component {
  val resets = List[ResetParameter](ResetParameter("system", 64), ResetParameter("debug", 64))
  val clocks = List[ClockParameter](
    ClockParameter("system", 100 MHz, "system"),
    ClockParameter("debug", 100 MHz, "debug", synchronousWith = "system")
  )

  val kitParameter = KitParameter(resets, clocks)
  val boardParameter = Nexys4DDR.Parameter(kitParameter)
  val socParameter = HydrogenTest.Parameter(boardParameter)
  val parameter = Hydrogen.Parameter(
    socParameter,
    128 kB,
    (resetCtrl: ResetControllerCtrl, _, clock: Bool) => { resetCtrl.buildXilinx(clock) },
    (clockCtrl: ClockControllerCtrl, resetCtrl: ResetControllerCtrl, clock: Bool) => {
      clockCtrl.buildXilinxPll(
        clock,
        boardParameter.getOscillatorFrequency,
        List("system", "debug"),
        10
      )
    }
  )

  val io = new Bundle {
    val clock = XilinxCmosIo("E3").clock(boardParameter.getOscillatorFrequency)
    val jtag = new Bundle {
      val tms = XilinxCmosIo("H2")
      val tdi = XilinxCmosIo("G4")
      val tdo = XilinxCmosIo("G2")
      val tck = XilinxCmosIo("F3").clock(boardParameter.getJtagFrequency).disableDedicatedClockRoute
    }
    val uartStd = new Bundle {
      val txd = XilinxCmosIo("D4")
      val rxd = XilinxCmosIo("C4")
      val rts = XilinxCmosIo("D3")
      val cts = XilinxCmosIo("E5")
    }
    val gpioStatus = Vec(
      XilinxCmosIo("R12"),
      XilinxCmosIo("R11"),
      XilinxCmosIo("G14"),
      XilinxCmosIo("N16")
    )
    val gpioA = Vec(
      XilinxCmosIo("J15"),
      XilinxCmosIo("L16"),
      XilinxCmosIo("M13"),
      XilinxCmosIo("R15"),
      XilinxCmosIo("R17"),
      XilinxCmosIo("T18"),
      XilinxCmosIo("U18"),
      XilinxCmosIo("R13"),
      XilinxCmosIo("T8"),
      XilinxCmosIo("U8"),
      XilinxCmosIo("R16"),
      XilinxCmosIo("T13"),
      XilinxCmosIo("H6"),
      XilinxCmosIo("U12"),
      XilinxCmosIo("U11"),
      XilinxCmosIo("V10"),
      XilinxCmosIo("H17"),
      XilinxCmosIo("K15"),
      XilinxCmosIo("J13"),
      XilinxCmosIo("N14"),
      XilinxCmosIo("R18"),
      XilinxCmosIo("V17"),
      XilinxCmosIo("U17"),
      XilinxCmosIo("U16"),
      XilinxCmosIo("V16"),
      XilinxCmosIo("T15"),
      XilinxCmosIo("U14"),
      XilinxCmosIo("T16"),
      XilinxCmosIo("V15"),
      XilinxCmosIo("V14"),
      XilinxCmosIo("V12"),
      XilinxCmosIo("V11")
    )
    val spiA = new Bundle {
      val ss = XilinxCmosIo("D14")
      val sclk = XilinxCmosIo("F16")
      val mosi = XilinxCmosIo("G16")
      val miso = XilinxCmosIo("H14")
    }
    val i2cA = new Bundle {
      val scl = XilinxCmosIo("C14")
      val sda = XilinxCmosIo("C15")
    }
    val freqCounterA = XilinxCmosIo("C17").clock(100 MHz).disableDedicatedClockRoute
    val pioA = Vec(XilinxCmosIo("V11"), XilinxCmosIo("V12"))
  }

  val soc = HydrogenTest(parameter)

  io.clock <> IBUF(soc.io_plat.clock)

  io.jtag.tms <> IBUF(soc.io_plat.jtag.tms)
  io.jtag.tdi <> IBUF(soc.io_plat.jtag.tdi)
  io.jtag.tdo <> OBUF(soc.io_plat.jtag.tdo)
  io.jtag.tck <> IBUF(soc.io_plat.jtag.tck)

  io.uartStd.txd <> OBUF(soc.io_per.uartStd.txd)
  io.uartStd.rxd <> IBUF(soc.io_per.uartStd.rxd)
  io.uartStd.rts <> OBUF(soc.io_per.uartStd.rts)
  io.uartStd.cts <> IBUF(soc.io_per.uartStd.cts)

  io.spiA.ss <> OBUF(soc.io_per.spiA.ss(0))
  io.spiA.sclk <> OBUF(soc.io_per.spiA.sclk)
  io.spiA.mosi <> OBUF(soc.io_per.spiA.mosi)
  io.spiA.miso <> IBUF(soc.io_per.spiA.miso)

  io.i2cA.scl <> IOBUF(soc.io_per.i2cA.scl.read, False, soc.io_per.i2cA.scl.write)
  io.i2cA.sda <> IOBUF(soc.io_per.i2cA.sda.read, False, soc.io_per.i2cA.sda.write)

  io.freqCounterA <> IBUF(soc.io_per.freqCounterA.clock)

  for (index <- 0 until 4) {
    io.gpioStatus(index) <> IOBUF(soc.io_per.gpioStatus.pins(index))
  }

  for (index <- 0 until 32) {
    io.gpioA(index) <> IOBUF(soc.io_per.gpioA.pins(index))
  }

  for (index <- 0 until 2) {
    io.pioA(index) <> IOBUF(soc.io_per.pioA.pins(index))
  }
}

object Nexys4DDRPrepare extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()

    top.soc.prepareZephyr("zephyr0", elementsConfig)

    val xdc = XilinxTools.Xdc(elementsConfig)
    top.soc.clockCtrl.generatedClocks foreach { clock => xdc.addGeneratedClock(clock) }
    xdc.generate(top.io)

    val embench = EmbenchIotTools(elementsConfig)
    embench.generate(top.soc.clockCtrl.getClockDomainByName("system").frequency.getValue)

    top
  }
}

object Nexys4DDRGenerate extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()
    top.soc.initOnChipRam(elementsConfig.swStorageZephyrBinary("zephyr0"))
    top
  }
}

object Nexys4DDRSimulate extends ElementsApp {
  val compiled = elementsConfig.genFPGASimConfig.compile {
    val board = Nexys4DDRBoard()
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
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "boot" =>
      compiled.doSimUntilVoid("boot") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.boot(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "mtimer" =>
      compiled.doSimUntilVoid("mtimer") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 400 ms)
        testCases.heartbeat(dut.io.gpioStatus(0))
      }
    case "gpio" =>
      compiled.doSimUntilVoid("gpio") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 1 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.gpioLoopback(dut.io.gpioA(0), dut.io.gpioA(2))
      }
    case "uart" =>
      compiled.doSimUntilVoid("uart") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 1 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.uartLoopback(dut.io.uartStd.txd, dut.io.uartStd.rxd, dut.baudPeriod)
      }
      compiled.doSimUntilVoid("uart-irq") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 1 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.uartIrq(dut.io.uartStd.txd, dut.io.uartStd.rxd, dut.baudPeriod)
      }
    case "frequency" =>
      compiled.doSimUntilVoid("100Mhz") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.frequency(dut.io.freqCounterA, 100 MHz, dut.io.uartStd.txd, dut.baudPeriod)
      }
      compiled.doSimUntilVoid("33Mhz") { dut =>
        val testCases = TestCases()
        dut.simHook()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.frequency(dut.io.freqCounterA, 33 MHz, dut.io.uartStd.txd, dut.baudPeriod)
      }
      compiled.doSimUntilVoid("20Mhz") { dut =>
        val testCases = TestCases()
        dut.simHook()
        testCases.addClockWithTimeout(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.frequency(dut.io.freqCounterA, 20 MHz, dut.io.uartStd.txd, dut.baudPeriod)
      }
    case "pio" =>
      compiled.doSimUntilVoid("write") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.pioWrite(dut.io.pioA(0), dut.baudPeriod)
      }
      compiled.doSimUntilVoid("read") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 10 ms)
        testCases.dump(dut.io.uartStd.txd, dut.baudPeriod)
        testCases.pioRead(dut.io.uartStd.txd, dut.baudPeriod)
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
