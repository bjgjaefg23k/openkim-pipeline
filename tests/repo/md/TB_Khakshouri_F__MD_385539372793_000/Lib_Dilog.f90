
    module Lib_Dilog
!---^^^^^^^^^^^^^^^^
!*      compute the dilogarithm function numerically
!*          Li2( - e^mu ) = - int_0^infty x/(exp(x-mu) + 1) dx
!*      and store as a quintic spline parameterized in mu
!*      ie dilog(mu) = Li2( - e^mu )
!*
!*      Author      :   Daniel Mason
!*      Version     :   1.0
!*      Revision    :   Feb 2012
!*


        use Lib_QuinticSpline
        implicit none
        private

        public      ::      initialise_qdilog
        public      ::      dilog
        public      ::      ddilog

        logical,private                     ::      qdilog_initialized = .false.
        type(quinticSpline),public          ::      qdilog

        integer,private,parameter           ::      DILOG_NINTGRL = 1000

    contains
!---^^^^^^^^

        pure function dilog(mu) result( li2 )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute Li2( - e^mu ) = - int_0^infty x/(exp(x-mu) + 1) dx
            real(kind=8),intent(in)         ::      mu
            real(kind=8)                    ::      li2

            real(kind=8)            ::      xx
            real(kind=8)            ::      xmax,dx
            integer         ::      ii
            if (qdilog_initialized) then
                li2 = splint( qdilog,mu )
            else
                xmax = mu + 100.0
                dx = xmax/DILOG_NINTGRL
                li2 = 0.0   !   = xx/(exp(xx-mu)+1) for xx = 0
                do ii = 1,DILOG_NINTGRL-1,2   !   sum using simpson's rule 1 4 2 4 2 ... 4 1
                    xx = ii*dx
                    if ( (xx-mu) < 100.0 ) li2 = li2 + 4*xx/(exp(xx-mu)+1)
                    xx = (ii+1)*dx
                    if ( (xx-mu) < 100.0 ) li2 = li2 + 2*xx/(exp(xx-mu)+1)
                end do
                if ( (xmax-mu) < 100.0 ) li2 = li2 - xmax/(exp(xmax-mu)+1)   ! correct last entry ( should be basically zero anyway )
                li2 = -li2 * dx / 3.0
            end if
            return
        end function dilog

        subroutine ddilog(mu ,y,dy,d2y,d3y,d4y)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      interpolate Li2( - e^mu ) function and find derivatives with respect to mu
    !*      Li2( - e^mu ) = - int_0^infty x/(exp(x-mu) + 1) dx
            real(kind=8),intent(in)                         ::      mu
            real(kind=8),intent(out)                        ::      y
            real(kind=8),intent(out)                        ::      dy
            real(kind=8),intent(out),optional               ::      d2y
            real(kind=8),intent(out),optional               ::      d3y
            real(kind=8),intent(out),optional               ::      d4y
            call initialise_qdilog()
            if (present(d3y)) then
                if (present(d4y)) then
                    call qsplint(qdilog,mu ,y,dy,d2y,d3y,d4y)
                else
                    call qsplint(qdilog,mu ,y,dy,d2y,d3y)
                end if
            else
                if (present(d2y)) then
                    call qsplint(qdilog,mu ,y,dy,d2y)
                else
                    call qsplint(qdilog,mu ,y,dy)
                end if
            end if
            return
        end subroutine ddilog


        subroutine initialise_qdilog()
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            real(kind=8),dimension(:),pointer       ::      mu
            real(kind=8),dimension(:),pointer       ::      li2
            integer     ::      ii,jj
            if (qdilog_initialized) return
            allocate(mu(75))
            allocate(li2(75))
            do ii = 1,8
                mu(ii)  = real(ii*10 - 110,kind=8)     !   -100:-30
            end do
            do ii = 1,19
                mu(8+ii) = real(ii - 21,kind=8)        !   -20:-2
            end do
            do ii = 1,20
                mu(27+ii) = real(ii*0.1 - 1.1,kind=8)  !   -1:0.9
            end do
            do ii = 1,19
                mu(47+ii) = real(ii,kind=8)            !   2:20
            end do
            do ii = 1,9
                mu(66+ii) = real(ii*10+10,kind=8)         !   30:100
            end do
            do ii = 1,75
                li2(ii) = dilog(mu(ii))
            end do
            qdilog = quinticSpline_ctor( mu,li2 )
            qdilog_initialized = .true.
            return
        end subroutine initialise_qdilog


    end module Lib_Dilog

!
!     program testLib_Dilog
! !---^^^^^^^^^^^^^^^^^^^^^
!
!         use Lib_Dilog
!         use Lib_quinticSpline
!         implicit none
!
!         integer     ::      ii
!         real(kind=8)        ::      mu,dilogmu,ddilogmu
!         print *,""
!         print *,"dilog test program"
!         print *,""
!
!         call initialise_qdilog()
!         call report(qdilog)
!
!         write (*,fmt='(4a16)') "mu","dilogmu","ddilogdmu","ddilogdmu(num)"
!         do ii = -20,20
!             mu = ii*1.0
!             call ddilog(mu ,dilogmu,ddilogmu)
!             write (*,fmt='(4f16.8)') mu,dilogmu,ddilogmu,( dilog( mu+0.01 )-dilog( mu-0.01 ) )/0.02
!         end do
!
!         call delete(qdilog)
!         print *,""
!         print *,"done"
!         print *,""
!
!     end program testLib_Dilog
!


